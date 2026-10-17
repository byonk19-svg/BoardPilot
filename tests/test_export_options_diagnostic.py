"""Diagnostic guardrails without launching native CAD or touching the application."""
from copy import deepcopy
import io
import os
import subprocess
import zipfile

import pytest

from diagnostics.export_options import (
    DiagnosticError, assert_only_change, assert_same_geometry,
    cache_namespace, recreate_cache, scan_blob,
)
from woodwork.templates import default_project_spec
from woodwork.application import compile_design


def test_option_change_rejects_unrelated_spec_mutation():
    before=default_project_spec();after=deepcopy(before)
    after['manufacturing']['saw_kerf_mm']='4'
    assert_only_change(before,after,('manufacturing','saw_kerf_mm'))
    after['dimensions']['outside_width_mm']='914.4'
    with pytest.raises(DiagnosticError):assert_only_change(before,after,('manufacturing','saw_kerf_mm'))


def test_geometry_comparison_requires_definitions_and_world_poses():
    before=compile_design(default_project_spec());after=deepcopy(before)
    assert_same_geometry(before,after)
    after['part_instances'][0]['center_mm']['x']='100'
    with pytest.raises(DiagnosticError):assert_same_geometry(before,after)


def test_marker_scan_checks_zip_payload_and_never_echoes_marker():
    marker=b'synthetic-private-test-value'
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('plain.txt',b'prefix '+marker+b' suffix')
    with pytest.raises(DiagnosticError) as error:scan_blob(stream.getvalue(),marker,'project.zip')
    assert marker.decode() not in str(error.value)
    assert 'project.zip' in str(error.value)
    assert scan_blob(b'ordinary data',marker,'plain.txt')==1


def test_cache_recreation_preserves_committed_artifacts(tmp_path):
    appdata=tmp_path/'appdata';root=appdata/'WoodworkingPlanner/data';root.mkdir(parents=True)
    lock=tmp_path/'lock';lock.write_bytes(b'pinned-lock')
    cache=cache_namespace(root,lock,appdata)
    cache.mkdir(parents=True);(cache/'generated.tmp').write_bytes(b'disposable')
    artifact=root/'artifacts/set_keep/assembly.step';artifact.parent.mkdir(parents=True);artifact.write_bytes(b'meaningful')
    report=recreate_cache(root,lock,appdata)
    assert report['status']=='passed' and cache.is_dir() and not list(cache.iterdir())
    assert artifact.read_bytes()==b'meaningful'


def test_cache_recreation_rejects_root_outside_appdata_and_missing_namespace(tmp_path):
    appdata=tmp_path/'appdata';appdata.mkdir();outside=tmp_path/'outside';outside.mkdir()
    lock=tmp_path/'lock';lock.write_bytes(b'pinned-lock')
    with pytest.raises(DiagnosticError):cache_namespace(outside,lock,appdata)
    root=appdata/'data';root.mkdir()
    with pytest.raises(DiagnosticError):recreate_cache(root,lock,appdata)


def test_cache_recreation_skips_links_without_deleting_target(tmp_path):
    appdata=tmp_path/'appdata';root=appdata/'data';root.mkdir(parents=True)
    lock=tmp_path/'lock';lock.write_bytes(b'pinned-lock');cache=cache_namespace(root,lock,appdata);cache.mkdir(parents=True)
    protected=tmp_path/'protected';protected.mkdir();(protected/'keep.txt').write_text('preserved')
    try:(cache/'link').symlink_to(protected,target_is_directory=True)
    except OSError:
        if os.name!='nt':pytest.skip('Creating a symlink requires unavailable host permission.')
        link_path=str(cache/'link').replace("'","''");target_path=str(protected).replace("'","''")
        code=f"New-Item -ItemType Junction -Path '{link_path}' -Target '{target_path}' -ErrorAction Stop | Out-Null"
        result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',code],capture_output=True,text=True,timeout=15)
        assert result.returncode==0,'Native Windows junction creation failed.'
    with pytest.raises(DiagnosticError):recreate_cache(root,lock,appdata)
    assert (protected/'keep.txt').read_text()=='preserved'
