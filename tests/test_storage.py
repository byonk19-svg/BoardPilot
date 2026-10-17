"""Revision/publication state tests; synthetic metadata is not CAD acceptance."""
from copy import deepcopy
import pytest
from woodwork.storage import Store, StoreError
from woodwork.templates import default_project_spec

def changed(spec):
    value=deepcopy(spec)
    value['dimensions']['outside_width_mm']='914.4'
    return value

def publish_metadata(store, project, revision, job, set_id, capabilities=('geometry',), source=None):
    # Only test the database pointer protocol. The dispatcher must separately
    # verify genuine artifact bytes before it calls this internal method.
    manifest={'project_id':project['id'],'revision_id':revision['id'],'artifact_set_id':set_id,'spec_sha256':revision['spec_sha256'],'resolved_sha256':revision['resolved_sha256'],'capabilities':list(capabilities),'source_artifact_set_id':source,'artifacts':[]}
    with store.transaction() as db:
        db.execute("UPDATE jobs SET state='running',owner_session='simulated-completed-callback' WHERE id=?",(job['id'],))
    return store.publish_result(job['id'], manifest, f'artifacts/{set_id}', 'a'*64)

def test_revisions_cas_invalid_input_and_reopen(tmp_path):
    store=Store(tmp_path)
    initial=store.create_project('Test',default_project_spec())
    project, first=initial['project'],initial['revision']
    result=store.create_revision(project['id'],first['id'],changed(first['spec']))
    second=result['revision']
    assert second['number']==2 and second['parent_id']==first['id']
    assert result['diff']['parts']['panel_horizontal']['after']['length_mm']=='878.4'
    with pytest.raises(StoreError) as error:
        store.create_revision(project['id'],first['id'],first['spec'])
    assert error.value.status==409
    reopened=Store(tmp_path)
    assert reopened.get_project(project['id'])['latest_accepted_revision_id']==second['id']
    assert reopened.get_revision(first['id'])['spec']['dimensions']['outside_width_mm']=='762'

def test_late_result_stays_historical_and_cumulative_capabilities_do_not_downgrade(tmp_path):
    store=Store(tmp_path)
    initial=store.create_project('Test',default_project_spec())
    project,first=initial['project'],initial['revision']
    oldjob=store.queue_job(first['id'],'generate','r1')
    second=store.create_revision(project['id'],first['id'],changed(first['spec']))['revision']
    newjob=store.queue_job(second['id'],'generate','r2')
    publish_metadata(store,project,second,newjob,'new_geometry')
    publish_metadata(store,project,first,oldjob,'old_geometry')
    assert store.get_project(project['id'])['latest_successful_revision_id']==second['id']
    docs=store.queue_job(second['id'],'documents','docs',source_artifact_set_id='new_geometry')
    publish_metadata(store,project,second,docs,'new_docs',('geometry','documents'),'new_geometry')
    sibling=store.queue_job(second['id'],'generate','sibling')
    publish_metadata(store,project,second,sibling,'sibling_geometry')
    assert store.get_revision(second['id'])['preferred_artifact_set_id']=='new_docs'
    package=store.queue_job(second['id'],'package','zip')
    stock=store.queue_job(second['id'],'stock','stock',source_artifact_set_id='new_docs')
    publish_metadata(store,project,second,stock,'new_stock',('geometry','documents','stock_layout'),'new_docs')
    assert store.get_job(package['id'])['source_artifact_set_id']=='new_docs'
    assert store.queue_job(second['id'],'package','zip')['id']==package['id']

def test_queue_idempotency_capacity_cancel_and_restart(tmp_path):
    store=Store(tmp_path)
    initial=store.create_project('Test',default_project_spec())
    revision=initial['revision']
    job=store.queue_job(revision['id'],'generate','same')
    assert store.queue_job(revision['id'],'generate','same')['id']==job['id']
    with pytest.raises(StoreError) as conflict:
        store.queue_job(revision['id'],'generate','same',source_artifact_set_id='changed_request')
    assert conflict.value.status==409
    assert store.cancel_job(job['id'])['state']=='cancelled'
    assert store.cancel_job(job['id'])['state']=='cancelled'
    running=store.queue_job(revision['id'],'generate','running')
    claimed=store.claim_job('session')
    assert claimed['id']==running['id'] and claimed['state']=='running'
    for i in range(10):store.queue_job(revision['id'],'generate',f'queued{i}')
    with pytest.raises(StoreError) as full:store.queue_job(revision['id'],'generate','overflow')
    assert full.value.status==429
    Store(tmp_path).recover_interrupted_jobs()
    assert store.get_job(running['id'])['state']=='interrupted'
    assert store.get_revision(revision['id'])['spec']==revision['spec']

def test_cross_project_base_and_artifact_set_are_rejected(tmp_path):
    store=Store(tmp_path)
    a=store.create_project('A',default_project_spec())
    b=store.create_project('B',default_project_spec())
    with pytest.raises(StoreError):store.create_revision(a['project']['id'],b['revision']['id'],default_project_spec())
    job=store.queue_job(a['revision']['id'],'generate','a')
    publish_metadata(store,a['project'],a['revision'],job,'a_set')
    with pytest.raises(StoreError):store.queue_job(b['revision']['id'],'documents','foreign',source_artifact_set_id='a_set')


def test_queued_job_cannot_publish_unclaimed_result(tmp_path):
    store=Store(tmp_path)
    initial=store.create_project('Test',default_project_spec());revision=initial['revision']
    job=store.queue_job(revision['id'],'generate','unclaimed')
    manifest={'project_id':initial['project']['id'],'revision_id':revision['id'],'artifact_set_id':'unclaimed_set','spec_sha256':revision['spec_sha256'],'resolved_sha256':revision['resolved_sha256'],'capabilities':['geometry'],'source_artifact_set_id':None,'artifacts':[]}
    with pytest.raises(StoreError) as error:store.publish_result(job['id'],manifest,'artifacts/unclaimed_set','a'*64)
    assert error.value.code=='JOB_NOT_PUBLISHABLE'


def test_explicit_cancellation_intent_survives_coordinator_restart(tmp_path):
    store=Store(tmp_path);initial=store.create_project('Cancel intent',default_project_spec());revision=initial['revision']
    job=store.queue_job(revision['id'],'generate','cancel-before-crash');store.claim_job('session')
    assert store.cancel_job(job['id'])['state']=='cancelling'
    store.recover_interrupted_jobs()
    assert store.get_job(job['id'])['state']=='cancelled'
    manifest={'project_id':initial['project']['id'],'revision_id':revision['id'],'artifact_set_id':'cancelled_set','spec_sha256':revision['spec_sha256'],'resolved_sha256':revision['resolved_sha256'],'capabilities':['geometry'],'source_artifact_set_id':None,'artifacts':[]}
    with pytest.raises(StoreError):store.publish_result(job['id'],manifest,'artifacts/cancelled_set','a'*64)
