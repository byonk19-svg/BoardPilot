from fastapi.testclient import TestClient
from woodwork.api import create_app
from woodwork.templates import default_project_spec

def client_for(root):
    app=create_app(root,start_dispatcher=False,testing=True)
    client=TestClient(app)
    token=client.get('/api/v1/session').json()['csrf_token']
    client.headers['X-Woodwork-CSRF']=token
    return client

def test_local_boundary_and_structured_input_validation(tmp_path):
    client=client_for(tmp_path)
    assert client.get('/api/v1/health',headers={'Host':'evil.example'}).status_code==403
    assert client.post('/api/v1/specs/validate',json=default_project_spec(),headers={'Origin':'https://evil.example'}).status_code==403
    no_token=TestClient(create_app(tmp_path/'other',start_dispatcher=False,testing=True))
    assert no_token.post('/api/v1/specs/validate',json=default_project_spec()).status_code==403
    result=client.post('/api/v1/inputs/normalize',json=[{'field':'dimensions.outside_width_mm','text':'30 1/2 in','default_unit':'in'}])
    assert result.status_code==200 and result.json()['values'][0]['value_mm']=='774.7'
    invalid=default_project_spec()
    invalid['dimensions']['outside_width_mm']='36'
    result=client.post('/api/v1/specs/validate',json=invalid)
    assert result.status_code==422
    assert any(f['code']=='INSIDE_WIDTH_NOT_POSITIVE' for f in result.json()['error']['details']['findings'])
    result=client.post('/api/v1/projects',content='{"broken":',headers={'Content-Type':'application/json'})
    assert result.status_code==400

def test_create_draft_revisions_idempotent_jobs_and_cancel(tmp_path):
    client=client_for(tmp_path)
    created=client.post('/api/v1/projects',json={'title':'Reference plywood bookcase','spec':default_project_spec()})
    assert created.status_code==201
    project,revision=created.json()['project'],created.json()['revision']
    assert revision['resolved']['part_instance_count']==7
    draft={'width':'bad','unit':'in'}
    assert client.put(f"/api/v1/projects/{project['id']}/draft",json={'base_revision_id':revision['id'],'raw':draft}).status_code==200
    assert client.get(f"/api/v1/projects/{project['id']}").json()['draft']['raw']==draft
    payload={'kind':'generate','idempotency_key':'once'}
    a=client.post(f"/api/v1/revisions/{revision['id']}/jobs",json=payload)
    b=client.post(f"/api/v1/revisions/{revision['id']}/jobs",json=payload)
    assert a.status_code==b.status_code==202 and a.json()['job']['id']==b.json()['job']['id']
    job=a.json()['job']
    assert client.post(f"/api/v1/jobs/{job['id']}/cancel",json={}).json()['job']['state']=='cancelled'
    assert client.post(f"/api/v1/jobs/{job['id']}/cancel",json={}).json()['job']['state']=='cancelled'
    spec=default_project_spec();spec['dimensions']['outside_width_mm']='914.4'
    next_revision=client.post(f"/api/v1/projects/{project['id']}/revisions",json={'base_revision_id':revision['id'],'spec':spec})
    assert next_revision.status_code==201 and next_revision.json()['diff']['parts']['panel_horizontal']['after']['length_mm']=='878.4'
    stale=client.post(f"/api/v1/projects/{project['id']}/revisions",json={'base_revision_id':revision['id'],'spec':spec})
    assert stale.status_code==409
    assert client.get('/api/v1/artifacts/not-found/download').status_code==404
    assert client.post(f"/api/v1/revisions/{revision['id']}/jobs",json={**payload,'executable':'untrusted'}).status_code==422
    reopened=client_for(tmp_path)
    assert reopened.get(f"/api/v1/projects/{project['id']}").json()['project']['latest_accepted_revision_id']==next_revision.json()['revision']['id']

def test_oversized_json_rejected_before_project_write(tmp_path):
    client=client_for(tmp_path)
    result=client.post('/api/v1/projects',content=b' '* (256*1024+1),headers={'Content-Type':'application/json'})
    assert result.status_code==413
    assert client.get('/api/v1/projects').json()['projects']==[]


def test_application_shell_revalidates_after_a_local_build(tmp_path):
    from woodwork.api.app import ApplicationFiles
    (tmp_path/'index.html').write_text('<script src="/assets/old.js"></script>',encoding='utf-8')
    client=TestClient(ApplicationFiles(directory=tmp_path,html=True))
    response=client.get('/')
    assert response.status_code==200
    assert response.headers.get('cache-control')=='no-cache'
    unchanged=client.get('/',headers={'If-None-Match':response.headers['etag']})
    assert unchanged.status_code==304
    assert unchanged.headers.get('cache-control')=='no-cache'
    (tmp_path/'index.html').write_text('<script src="/assets/new-build.js"></script>',encoding='utf-8')
    updated=client.get('/',headers={'If-None-Match':response.headers['etag']})
    assert updated.status_code==200
    assert 'new-build.js' in updated.text
