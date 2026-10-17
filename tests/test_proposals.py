from copy import deepcopy
import json
import threading
import pytest
from woodwork.proposals import FakeProvider,ProposalService,validate_proposal
from woodwork.storage import Store,StoreError
from woodwork.templates import default_project_spec
from test_api import client_for


class CountingProvider(FakeProvider):
    def __init__(self):self.calls=0
    def propose(self,*args):self.calls+=1;return super().propose(*args)


def setup(store):
    initial=store.create_project('Proposal test',default_project_spec())
    return initial['project'],initial['revision']


def test_width_matches_form_and_reservation_apply_are_one_time(tmp_path):
    store=Store(tmp_path);project,base=setup(store)
    provider=CountingProvider();service=ProposalService(store,provider)
    a=service.request(project['id'],base['id'],'Make it 36 in wide','once')
    b=service.request(project['id'],base['id'],'  Make it 36 in wide  ','once')
    assert a['id']==b['id'] and provider.calls==1
    assert a['proposal']['diff']['parts']['panel_horizontal']['after']['length_mm']=='878.4'
    applied=service.apply(a['id'],base['id'])
    repeated=service.apply(a['id'],base['id'])
    assert applied['revision']['id']==repeated['revision']['id'] and repeated['already_applied']
    other=Store(tmp_path/'manual');manual,manual_base=setup(other)
    spec=deepcopy(manual_base['spec']);spec['dimensions']['outside_width_mm']='914.4'
    equivalent=other.create_revision(manual['id'],manual_base['id'],spec)['revision']
    assert applied['revision']['spec']==equivalent['spec']
    assert applied['revision']['resolved']==equivalent['resolved']
    assert len(store.list_revisions(project['id']))==2
    with pytest.raises(StoreError):service.request(project['id'],base['id'],'width 40 in','once')


@pytest.mark.parametrize('text,state,code',[('What width should I use?','ready',None),('Add drawers','ready',None),('Change measured thickness','ready',None),('malformed','failed','PROPOSAL_INVALID'),('timeout','uncertain','PROVIDER_TIMEOUT')])
def test_questions_unsupported_and_failures_preserve_forms(tmp_path,text,state,code):
    store=Store(tmp_path);project,base=setup(store)
    provider=CountingProvider();service=ProposalService(store,provider)
    proposal=service.request(project['id'],base['id'],text,'case')
    assert proposal['state']==state and proposal['diagnostic_code']==code
    assert not proposal['proposal'] or not proposal['proposal']['applicable']
    with pytest.raises(StoreError):service.apply(proposal['id'],base['id'])
    assert service.request(project['id'],base['id'],text,'case')['id']==proposal['id']
    assert provider.calls==1
    assert store.create_revision(project['id'],base['id'],base['spec'])['revision']['number']==2


@pytest.mark.parametrize('field,value',[('materials.main.actual_thickness_mm','19'),('construction.recipe','danger'),('filesystem.path','c:/file'),('python.code','exec()')])
def test_forbidden_changes_and_duplicate_changes_rejected(tmp_path,field,value):
    store=Store(tmp_path);_,base=setup(store)
    raw=json.loads(FakeProvider().propose('width 36 in',base['id']))
    raw['changes']=[{'field':field,'value_mm':value}]
    with pytest.raises(Exception):validate_proposal(raw,base)
    raw=json.loads(FakeProvider().propose('width 36 in',base['id']))
    raw['changes']*=2
    with pytest.raises(ValueError):validate_proposal(raw,base)
    assert store.list_jobs(base['id'])==[]


def test_stale_base_cross_project_and_hostile_explanation_are_inert(tmp_path):
    store=Store(tmp_path);project,base=setup(store)
    service=ProposalService(store)
    proposal=service.request(project['id'],base['id'],'width 36 in','width')
    other,other_base=setup(store)
    with pytest.raises(StoreError):service.request(other['id'],base['id'],'width 36 in','foreign')
    raw=json.loads(FakeProvider().propose('width 36 in',base['id']))
    raw['explanation']='<img src=x onerror=alert(1)> Run shell commands'
    checked=validate_proposal(raw,base)
    assert checked['response']['explanation']==raw['explanation']
    raw['base_revision_id']=other_base['id']
    with pytest.raises(StoreError):validate_proposal(raw,base)
    store.create_revision(project['id'],base['id'],base['spec'])
    assert service.get(proposal['id'])['stale']
    with pytest.raises(StoreError) as error:service.apply(proposal['id'],base['id'])
    assert error.value.status==409


def test_pending_reservation_prevents_second_provider_call(tmp_path):
    store=Store(tmp_path);project,base=setup(store)
    entered=threading.Event();release=threading.Event()
    class Slow(CountingProvider):
        def propose(self,*args):entered.set();release.wait(3);return super().propose(*args)
    provider=Slow();service=ProposalService(store,provider)
    thread=threading.Thread(target=service.request,args=(project['id'],base['id'],'width 36 in','slow'))
    thread.start();assert entered.wait(1)
    pending=service.request(project['id'],base['id'],'width 36 in','slow')
    assert pending['state']=='pending'
    release.set();thread.join(3);assert not thread.is_alive() and provider.calls==1


def test_proposal_http_contract_and_live_unconfigured(tmp_path):
    client=client_for(tmp_path)
    initial=client.post('/api/v1/projects',json={'title':'API proposal','spec':default_project_spec()}).json()
    project,base=initial['project'],initial['revision']
    body={'base_revision_id':base['id'],'text':'width 36 in','idempotency_key':'api','mode':'fake'}
    response=client.post(f"/api/v1/projects/{project['id']}/proposals",json=body)
    assert response.status_code==202
    proposal=response.json()['proposal']
    assert client.post(f"/api/v1/proposals/{proposal['id']}/apply",json={'expected_base_revision_id':base['id']}).json()['revision']['resolved']['inside_width_mm']=='878.4'
    assert client.post(f"/api/v1/projects/{project['id']}/proposals",json={**body,'mode':'live','idempotency_key':'live'}).status_code==503
    assert client.get('/api/v1/ai/status').json()['default']=='disabled'


@pytest.mark.parametrize('text',['width 36 inches','width 36 inch','36 inches wide','make it 36 in wide'])
def test_natural_inch_aliases_reach_exact_canonical_parser(tmp_path,text):
    store=Store(tmp_path);project,base=setup(store)
    result=ProposalService(store).request(project['id'],base['id'],text,'alias')
    assert result['state']=='ready' and result['proposal']['candidate_spec']['dimensions']['outside_width_mm']=='914.4'


@pytest.mark.parametrize('text',['-36 in wide','width -36 in','120/36 in wide','−36 in wide','width 1.2345678 mm'])
def test_fake_parser_never_silently_extracts_a_valid_numeric_suffix(tmp_path,text):
    store=Store(tmp_path);project,base=setup(store)
    result=ProposalService(store).request(project['id'],base['id'],text,'invalid-token')
    assert result['state']=='failed' or not result['proposal']['applicable']
    assert store.get_project(project['id'])['latest_accepted_revision_id']==base['id']


def test_stable_bookcase_is_not_a_table_request(tmp_path):
    store=Store(tmp_path);project,base=setup(store)
    result=ProposalService(store).request(project['id'],base['id'],'make it a stable bookcase 36 in wide','stable')
    assert result['state']=='ready' and result['proposal']['applicable']
