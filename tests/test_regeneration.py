"""Regressions for live progress and the exact saved bytes inspected by CAD."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from woodwork.cad_adapter.runtime import _run_driver, validate_artifact_set
from woodwork.cad_adapter.verifier import CadValidationError
from woodwork.exports.core import sha256_file, write_json
from woodwork.jobs.environment import worker_environment
from woodwork.storage import Store
from woodwork.templates import default_project_spec


def test_geometry_font_hook_is_limited_to_system_registration(monkeypatch):
    import glob
    import runpy
    from woodwork.cad_adapter.runtime import DRIVERS
    original=glob.glob
    calls=[]
    monkeypatch.setattr(glob,'glob',lambda path,*a,**k: calls.append(path) or ['real-file'])
    try:
        runpy.run_path(str(DRIVERS.parent/'native_bootstrap/sitecustomize.py'))
        namespace={'__name__':'build123d.text','glob':glob}
        exec('def register_folder(path): return glob.glob(path)',namespace)
        if os.name=='nt':
            assert namespace['register_folder']('C:/Windows/Fonts/*ttf')==[]
            assert calls==[]
        assert glob.glob('C:/Windows/Fonts/*ttf')==['real-file']
        assert namespace['register_folder']('C:/app/bundled/*ttf')==['real-file']
        assert namespace['register_folder']('C:/Windows/Fonts/*json')==['real-file']
    finally:
        glob.glob=original


def test_transient_native_children_load_the_geometry_bootstrap(tmp_path,monkeypatch):
    from woodwork.cad_adapter.runtime import _cad_environment
    monkeypatch.setenv('OPENAI_API_KEY','test-only-credential-marker')
    probe="import glob,json,os,platform;print(json.dumps({'hook':getattr(glob.glob,'_woodwork_geometry_fonts',False),'wmi_disabled':getattr(platform,'_wmi',None) is None,'provider_present':'OPENAI_API_KEY' in os.environ}))"
    child=subprocess.run([sys.executable,'-P','-c',probe],env=_cad_environment(tmp_path),capture_output=True,text=True,timeout=20)
    assert child.returncode==0,child.stderr
    result=json.loads(child.stdout)
    assert result['hook']==(os.name=='nt')
    assert result['wmi_disabled']
    assert not result['provider_present']


@pytest.mark.parametrize('fail',[False,True])
def test_owned_driver_uses_only_curated_environment_and_restores_process_state(tmp_path,monkeypatch,fail):
    import glob
    from woodwork.cad_adapter import runtime
    monkeypatch.setattr(glob,'glob',glob.glob)
    original_argv=sys.argv; original_cwd=Path.cwd()
    monkeypatch.setenv('UNAPPROVED_PROVIDER_KEY','must-not-reach-cad')
    driver=tmp_path/'driver.py'
    driver.write_text("""import os,sys
from pathlib import Path
assert 'UNAPPROVED_PROVIDER_KEY' not in os.environ
assert os.environ['APPROVED_TEST']=='yes'
assert sys.argv==[__file__]
assert Path.cwd()==Path(__file__).parent
WOODWORK_PROGRESS('generating_side_panels')
WOODWORK_PROGRESS('private-message')
if os.environ['FAIL']=='yes': raise SystemExit(23)
""",encoding='utf-8')
    stages=[]
    # The runner is private to the single-job owned worker. Library builds retain
    # the subprocess route and never mutate their host's cwd/environment/argv.
    if fail:
        with pytest.raises(CadValidationError,match='exit code 23'):
            runtime._run_owned_driver(driver,{'APPROVED_TEST':'yes','FAIL':'yes'},progress=stages.append)
    else:
        runtime._run_owned_driver(driver,{'APPROVED_TEST':'yes','FAIL':'no'},progress=stages.append)
    assert stages==['generating_side_panels']
    assert sys.argv is original_argv and Path.cwd()==original_cwd
    assert os.environ['UNAPPROVED_PROVIDER_KEY']=='must-not-reach-cad'


def test_driver_progress_arrives_before_child_completion_and_ignores_raw_events(tmp_path):
    driver=tmp_path/'driver.py'; acknowledgement=tmp_path/'ack'
    driver.write_text("""import json,sys,time
from pathlib import Path
print(json.dumps({'model':'private-path','stage':'unsafe-stage'}),file=sys.stderr,flush=True)
print(json.dumps({'woodwork_stage':['assembling_geometry']}),file=sys.stderr,flush=True)
print('x'*20000,file=sys.stderr,flush=True)
print(json.dumps({'woodwork_stage':'generating_side_panels'}),file=sys.stderr,flush=True)
deadline=time.monotonic()+3
while not Path('ack').exists() and time.monotonic()<deadline: time.sleep(.01)
assert Path('ack').exists(), 'progress was buffered until the child exited'
print(json.dumps({'woodwork_stage':'unapproved-stage'}),file=sys.stderr,flush=True)
""",encoding='utf-8')
    stages=[]
    def progress(stage):
        stages.append(stage); acknowledgement.write_text('received')
    _run_driver(driver,dict(os.environ),progress=progress)
    assert stages==['generating_side_panels']


def test_cad_substages_are_persisted_but_arbitrary_worker_text_is_not(tmp_path):
    store=Store(tmp_path)
    created=store.create_project('Progress regression',default_project_spec())
    queued=store.queue_job(created['revision']['id'],'generate','stage-test')
    store.claim_job('stage-session')
    for stage in ('generating_side_panels','generating_horizontal_panels','generating_back_panel','assembling_geometry','verifying_artifacts'):
        store.update_stage(queued['id'],stage)
        assert store.get_job(queued['id'])['stage']==stage
    store.update_stage(queued['id'],'private-path-or-unapproved-message')
    assert store.get_job(queued['id'])['stage']=='verifying_artifacts'


def modern_inspection_fixture(tmp_path):
    source=Path(__file__).resolve().parents[1]/'samples/reference-bookcase'
    root=tmp_path/'set'; shutil.copytree(source,root)
    manifest=json.loads((root/'manifest.json').read_text())
    manifest['versions']['adapter']='1.1.0'
    # Exercise a geometry-only set: document bindings are a separate later gate.
    manifest['capabilities']=['geometry']
    manifest['validation'].update(documents='not_requested',stock_layout='not_requested')
    evidence=json.loads((root/'geometry-validation.json').read_text())
    evidence['cad_artifact_sha256']={a['relative_path']:a['sha256'] for a in manifest['artifacts'] if a['kind'] in {'step','glb'}}
    write_json(root/'geometry-validation.json',evidence)
    refresh_record(root,manifest,'geometry-validation.json')
    write_json(root/'manifest.json',manifest)
    return root,manifest


def refresh_record(root,manifest,relative):
    record=next(a for a in manifest['artifacts'] if a['relative_path']==relative)
    record.update(sha256=sha256_file(root/relative),size_bytes=(root/relative).stat().st_size)


def test_rehashed_part_cannot_reuse_an_earlier_geometry_inspection(tmp_path):
    root,manifest=modern_inspection_fixture(tmp_path)
    validate_artifact_set(root,inspect_geometry=False)
    relative='parts/panel_side.step'
    with (root/relative).open('ab') as stream: stream.write(b'\n/* changed after inspection */\n')
    refresh_record(root,manifest,relative); write_json(root/'manifest.json',manifest)
    with pytest.raises(CadValidationError,match='inspection.*bytes'):
        validate_artifact_set(root,inspect_geometry=False)


def test_new_adapter_cannot_omit_native_inspection_byte_bindings(tmp_path):
    root,manifest=modern_inspection_fixture(tmp_path)
    evidence=json.loads((root/'geometry-validation.json').read_text())
    del evidence['cad_artifact_sha256']
    write_json(root/'geometry-validation.json',evidence)
    refresh_record(root,manifest,'geometry-validation.json');write_json(root/'manifest.json',manifest)
    with pytest.raises(CadValidationError,match='inspection.*bytes'):
        validate_artifact_set(root,inspect_geometry=False)


def test_rehashed_step_selectors_must_match_the_native_inspection(tmp_path):
    root,manifest=modern_inspection_fixture(tmp_path)
    relative='step-instance-map.json'
    sidecar=json.loads((root/relative).read_text())
    first,second=sidecar['instances'][:2]
    first['selector'],second['selector']=second['selector'],first['selector']
    write_json(root/relative,sidecar)
    refresh_record(root,manifest,relative);write_json(root/'manifest.json',manifest)
    with pytest.raises(CadValidationError,match='inspection.*selectors'):
        validate_artifact_set(root,inspect_geometry=False)
