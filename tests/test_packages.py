import io
import json
import os
from pathlib import Path
import stat
import zipfile
import pytest
from woodwork.exports.package import build_package,verify_package
from woodwork.imports import inspect_import,accept_import
from woodwork.storage import Store,StoreError


def zipped(entries):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as archive:
        for name,data,mode in entries:
            info=zipfile.ZipInfo(name);info.external_attr=mode<<16
            archive.writestr(info,data)
    return stream.getvalue()


@pytest.mark.parametrize('name,mode',[('../escape.txt',0),('/absolute.txt',0),('c:/drive.txt',0),('nested\\escape.txt',0),('part.py',0),('link.txt',stat.S_IFLNK|0o777)])
def test_unsafe_import_inert_rejected_before_project_write(tmp_path,name,mode):
    with pytest.raises(StoreError) as error:inspect_import(zipped([(name,b'not executed',mode)]),tmp_path)
    assert error.value.code=='IMPORT_INVALID'
    assert Store(tmp_path).list_projects()==[]


def test_duplicate_and_oversized_expansion_rejected(tmp_path):
    with pytest.raises(StoreError):inspect_import(zipped([('project.json',b'{}',0),('project.json',b'{}',0)]),tmp_path)
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED) as archive:archive.writestr('project.json',b'0'*(2*1024*1024))
    with pytest.raises(StoreError):inspect_import(stream.getvalue(),tmp_path)


@pytest.mark.skipif(not os.environ.get('WOODWORK_PACKAGE_SOURCE'),reason='Set WOODWORK_PACKAGE_SOURCE to a genuine immutable output directory.')
def test_genuine_export_inventory_import_new_identity_and_corruption(tmp_path):
    source=Path(os.environ['WOODWORK_PACKAGE_SOURCE'])
    manifest=json.loads((source/'manifest.json').read_text())
    metadata={key:manifest[key] for key in ('project_id','revision_id','spec_sha256','resolved_sha256')}
    metadata['source_artifact_set_id']=manifest['artifact_set_id']
    result=build_package(source,tmp_path/'package',metadata)
    assert verify_package(tmp_path/'package/project.zip',manifest)['status']=='passed'
    data=(tmp_path/'package/project.zip').read_bytes()
    store=Store(tmp_path/'store')
    accepted=inspect_import(data,store.root)
    imported=accept_import(store,accepted['token'],'Reimported sample')
    assert imported['project']['id']!=manifest['project_id']
    assert imported['revision']['id']!=manifest['revision_id']
    assert imported['revision']['spec_sha256']==manifest['spec_sha256']
    assert imported['revision']['preferred_artifact_set_id'] is None
    assert imported['project']['provenance']['source_artifact_set_id']==manifest['artifact_set_id']
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries=[(n,archive.read(n),0) for n in archive.namelist()]
    entries=[(n,b'wrong revision' if n=='cut-list.csv' else payload,mode) for n,payload,mode in entries]
    with pytest.raises(StoreError):inspect_import(zipped(entries),store.root)
