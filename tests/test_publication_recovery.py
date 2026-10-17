from copy import deepcopy
import json
import os
from pathlib import Path
import pytest
from diagnostics.recovery import seed
from woodwork.exports.cumulative import copy_verified_set
from woodwork.exports.core import sha256_file,write_json
from woodwork.cad_adapter import validate_artifact_set
from woodwork.jobs.dispatcher import Dispatcher
from test_api import client_for

pytestmark=pytest.mark.skipif(not os.environ.get('WOODWORK_PACKAGE_SOURCE'),reason='Requires an actual genuine immutable source set.')


def test_rename_before_database_publication_is_verified_and_reconciled(tmp_path):
    source=Path(os.environ['WOODWORK_PACKAGE_SOURCE'])
    store,original=seed(tmp_path/'store',source)
    job=store.queue_job(original['revision_id'],'generate','fault-at-commit')
    store.claim_job('fault-session')
    # Verified real CAD bytes are reused in a new identity set for this controlled
    # publication-boundary injection, with every wrapper rebound and rehashed.
    metadata={k:original[k] for k in ('project_id','revision_id','revision_number','spec_sha256','resolved_sha256')}
    metadata.update(artifact_set_id='set_orphan',source_artifact_set_id=original['artifact_set_id'])
    staging=store.root/'staged-real-copy'
    manifest,records=copy_verified_set(source,staging,metadata)
    manifest['source_artifact_set_id']=None
    write_json(staging/'manifest.json',manifest)
    validate_artifact_set(staging,inspect_geometry=False)
    final=store.root/'artifacts/set_orphan'
    staging.rename(final)
    receipt={'job_id':job['id'],'relative_dir':'artifacts/set_orphan','manifest_sha256':sha256_file(final/'manifest.json')}
    (store.root/'receipts').mkdir()
    write_json(store.root/'receipts/set_orphan.json',receipt)
    assert store.get_job(job['id'])['state']=='running'
    dispatcher=Dispatcher(store)
    dispatcher.start()
    try:
        assert store.get_job(job['id'])['state']=='succeeded'
        assert store.get_revision(original['revision_id'])['preferred_artifact_set_id']=='set_orphan'
        assert store.get_artifact_set('set_orphan')['manifest_sha256']==receipt['manifest_sha256']
    finally:dispatcher.close()
    again=Dispatcher(store);again.start();again.close()
    assert len(store.list_artifact_sets(original['revision_id']))==2


def test_missing_corrupt_committed_artifact_and_disposable_cache(tmp_path):
    store,manifest=seed(tmp_path/'store',Path(os.environ['WOODWORK_PACKAGE_SOURCE']))
    client=client_for(store.root)
    endpoint=f"/api/v1/revisions/{manifest['revision_id']}/manifest"
    assert client.get(endpoint).status_code==200
    # Disposable cache never contains the sole committed copy.
    cache=store.root/'cache';cache.mkdir();(cache/'unrelated.tmp').write_text('cache only')
    import shutil
    shutil.rmtree(cache);cache.mkdir()
    assert client.get(endpoint).status_code==200
    record=next(a for a in manifest['artifacts'] if a['relative_path']=='cut-list.csv')
    path=store.root/'artifacts'/manifest['artifact_set_id']/'cut-list.csv'
    original=path.read_bytes();path.write_bytes(b'corrupted')
    assert client.get(endpoint).status_code==409
    assert client.get(f"/api/v1/artifacts/{record['artifact_id']}/download").status_code==409
    path.write_bytes(original);path.unlink()
    assert client.get(endpoint).status_code==409
    assert store.get_revision(manifest['revision_id'])['spec_sha256']==manifest['spec_sha256']


def test_injected_saved_geometry_inspection_exception_cannot_publish(tmp_path,monkeypatch):
    from types import SimpleNamespace
    import shutil
    from woodwork.cad_adapter import CadValidationError
    import woodwork.cad_adapter as adapter
    from woodwork.jobs import worker
    source=Path(os.environ['WOODWORK_PACKAGE_SOURCE'])
    store,manifest=seed(tmp_path/'store',source)
    queued=store.queue_job(manifest['revision_id'],'generate','inspection-fault')
    job=store.claim_job('inspection-test')
    def cached_build(spec,resolved,metadata,out,**kwargs):
        shutil.copytree(source,out)
        return json.loads((out/'manifest.json').read_text())
    def inspection_failure(*args,**kwargs):raise CadValidationError('Injected saved inspection exception')
    monkeypatch.setattr(adapter,'build_artifact_set',cached_build)
    monkeypatch.setattr(adapter,'validate_artifact_set',inspection_failure)
    class InjectedWorker:
        def run(self,args,**kwargs):
            with pytest.raises(CadValidationError):worker.main(Path(args[-1]))
            assert not (Path(args[-1])/'result.json').exists()
            return SimpleNamespace(returncode=1,timed_out=False,cancelled=False,elapsed_seconds=.01,peak_rss_bytes=0,log_tail='{"error_code":"CAD_INSPECTION_FAILED"}')
    dispatcher=Dispatcher(store);dispatcher.supervisor.close();dispatcher.supervisor=InjectedWorker()
    dispatcher.execute(job)
    result=store.get_job(queued['id'])
    assert result['state']=='failed' and result['diagnostic_code']=='CAD_INSPECTION_FAILED'
    assert store.get_revision(manifest['revision_id'])['preferred_artifact_set_id']==manifest['artifact_set_id']
    assert len(store.list_artifact_sets(manifest['revision_id']))==1


def test_real_rename_then_sqlite_commit_failure_recovers_on_restart(tmp_path,monkeypatch):
    import sqlite3
    from types import SimpleNamespace
    source=Path(os.environ['WOODWORK_PACKAGE_SOURCE'])
    store,original=seed(tmp_path/'store',source)
    queued=store.queue_job(original['revision_id'],'generate','database-commit-fault')
    job=store.claim_job('fault-after-rename')
    class VerifiedResult:
        def run(self,args,**kwargs):
            root=Path(args[-1]);payload=json.loads((root/'input.json').read_text());metadata=payload['metadata']
            manifest,_=copy_verified_set(source,root/'out',{**metadata,'source_artifact_set_id':original['artifact_set_id']})
            manifest['source_artifact_set_id']=None
            write_json(root/'out/manifest.json',manifest)
            return SimpleNamespace(returncode=0,timed_out=False,cancelled=False,elapsed_seconds=.01,peak_rss_bytes=0,log_tail='')
        def close(self):pass
    dispatcher=Dispatcher(store);dispatcher.supervisor.close();dispatcher.supervisor=VerifiedResult()
    original_publish=store.publish_result
    def failed_commit(*args,**kwargs):raise sqlite3.OperationalError('Injected database commit failure after rename')
    monkeypatch.setattr(store,'publish_result',failed_commit)
    (store.root/'receipts').mkdir()
    dispatcher.execute(job)
    result=store.get_job(queued['id'])
    assert result['state']=='interrupted' and result['diagnostic_code']=='PUBLICATION_PENDING'
    assert store.get_revision(original['revision_id'])['preferred_artifact_set_id']==original['artifact_set_id']
    assert len(list((store.root/'artifacts').iterdir()))==2
    monkeypatch.setattr(store,'publish_result',original_publish)
    dispatcher.start()
    try:
        recovered=store.get_job(job['id'])
        assert recovered['state']=='succeeded' and recovered['diagnostic_code'] is None
        assert store.get_revision(original['revision_id'])['preferred_artifact_set_id']==recovered['result_artifact_set_id']
    finally:dispatcher.close()


def test_result_identifier_rejected_before_filesystem_publication(tmp_path):
    from woodwork.storage import StoreError
    store,manifest=seed(tmp_path/'store',Path(os.environ['WOODWORK_PACKAGE_SOURCE']))
    dispatcher=Dispatcher(store)
    revision=store.get_revision(manifest['revision_id'])
    metadata={k:manifest[k] for k in ('project_id','revision_id','revision_number','artifact_set_id','source_artifact_set_id','spec_sha256','resolved_sha256')}
    value=deepcopy(manifest);value['artifact_set_id']='../../escape'
    with pytest.raises(StoreError):dispatcher.verify_result_identity(value,metadata,revision['resolved'])
    dispatcher.supervisor.close()


def test_genuine_renamed_receipt_cannot_override_cancellation_on_restart(tmp_path):
    source=Path(os.environ['WOODWORK_PACKAGE_SOURCE']);store,original=seed(tmp_path/'store',source)
    job=store.queue_job(original['revision_id'],'generate','cancelled-orphan');store.claim_job('cancel-session')
    metadata={k:original[k] for k in ('project_id','revision_id','revision_number','spec_sha256','resolved_sha256')}
    metadata.update(artifact_set_id='set_cancelled_orphan',source_artifact_set_id=original['artifact_set_id'])
    final=store.root/'artifacts/set_cancelled_orphan'
    manifest,_=copy_verified_set(source,final,metadata);manifest['source_artifact_set_id']=None
    write_json(final/'manifest.json',manifest)
    (store.root/'receipts').mkdir()
    write_json(store.root/'receipts/cancelled-orphan.json',{'job_id':job['id'],'relative_dir':'artifacts/set_cancelled_orphan','manifest_sha256':sha256_file(final/'manifest.json')})
    store.cancel_job(job['id'])
    dispatcher=Dispatcher(store);dispatcher.start();dispatcher.close()
    assert store.get_job(job['id'])['state']=='cancelled'
    assert store.get_revision(original['revision_id'])['preferred_artifact_set_id']==original['artifact_set_id']
    assert len(store.list_artifact_sets(original['revision_id']))==1
