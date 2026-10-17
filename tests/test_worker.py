import json
import subprocess
import sys
import platform
from woodwork.jobs.environment import worker_environment
from woodwork.templates import default_project_spec
from woodwork.domain import compile_project

def test_worker_rejects_code_fields_and_mixed_ledger_before_cad(tmp_path):
    spec=default_project_spec()
    job={'kind':'generate','spec':spec,'resolved':compile_project(spec),'metadata':{'project_id':'p','revision_id':'r','revision_number':1},'python_source':'raise Exception()'}
    (tmp_path/'input.json').write_text(json.dumps(job))
    result=subprocess.run([sys.executable,'-m','woodwork.jobs.worker',str(tmp_path)],env=worker_environment(tmp_path),capture_output=True,text=True,timeout=20)
    assert result.returncode!=0
    assert '"error_code": "JOB_CONTRACT_INVALID"' in result.stdout
    assert not (tmp_path/'out').exists()
    del job['python_source']
    job['spec']['dimensions']['outside_width_mm']='914.4'
    (tmp_path/'input.json').write_text(json.dumps(job))
    result=subprocess.run([sys.executable,'-m','woodwork.jobs.worker',str(tmp_path)],env=worker_environment(tmp_path),capture_output=True,text=True,timeout=20)
    assert result.returncode!=0
    assert '"error_code": "SOURCE_MISMATCH"' in result.stdout
    assert not (tmp_path/'out').exists()

def test_worker_rejects_invalid_metadata_before_native_launch(tmp_path):
    spec=default_project_spec()
    job={'kind':'generate','spec':spec,'resolved':compile_project(spec),'metadata':{'project_id':'p','revision_id':'r','revision_number':True,'executable':'untrusted'}}
    (tmp_path/'input.json').write_text(json.dumps(job))
    result=subprocess.run([sys.executable,'-m','woodwork.jobs.worker',str(tmp_path)],env=worker_environment(tmp_path),capture_output=True,text=True,timeout=20)
    assert result.returncode!=0
    assert '"error_code": "JOB_CONTRACT_INVALID"' in result.stdout
    assert not (tmp_path/'out').exists()

def test_provider_credentials_are_absent_from_worker_environment(tmp_path,monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','test-only-credential-marker')
    monkeypatch.setenv('ANTHROPIC_API_KEY','test-only-credential-marker')
    environment=worker_environment(tmp_path)
    assert not any('test-only-credential-marker' in value for value in environment.values())
    assert 'OPENAI_API_KEY' not in environment and 'ANTHROPIC_API_KEY' not in environment


def test_nested_cad_process_can_select_installed_native_tracer(tmp_path,monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','test-only-credential-marker')
    probe = """
import json, os, platform
# A Windows hardware query must not be attempted inside native CAD workers.
class BlockedWmi:
    def exec_query(self,query): raise AssertionError('Unexpected WMI query')
if os.name=='nt': platform._wmi=BlockedWmi()
from woodwork.cad_adapter.windows_runtime import configure_native_platform
configure_native_platform()
from cadgen._internal.filetrace import _library_name
from cadgen.assets import runtime_root
print(json.dumps({'machine':platform.machine(),'tracer_exists':(runtime_root()/'native'/_library_name()).is_file(),'provider_present':'OPENAI_API_KEY' in os.environ}))
"""
    intermediate = """
import subprocess, sys
from pathlib import Path
from woodwork.cad_adapter.runtime import _cad_environment
result=subprocess.run([sys.executable,'-c',sys.argv[1]],env=_cad_environment(Path(sys.argv[2])),capture_output=True,text=True,timeout=20)
print(result.stdout,end='')
raise SystemExit(result.returncode)
"""
    result=subprocess.run([sys.executable,'-c',intermediate,probe,str(tmp_path)],env=worker_environment(tmp_path),capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
    observed=json.loads(result.stdout)
    assert observed['machine']==platform.machine()
    assert observed['tracer_exists']
    assert not observed['provider_present']
