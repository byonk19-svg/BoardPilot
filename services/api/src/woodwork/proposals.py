"""Provider-neutral, schema-limited proposals with an explicitly offline demo."""
from copy import deepcopy
import json
from pathlib import Path
import re
import unicodedata
import jsonschema
from woodwork.application import compile_design
from woodwork.domain import hash_json,normalize_measurement,canonical_json
from woodwork.storage import StoreError,new_id,now,semantic_diff

SCHEMA=Path(__file__).resolve().parents[4]/'handoff/package/woodworking-codex-handoff/spec/ai-proposal.schema.json'
ALLOWED={'dimensions.outside_width_mm','dimensions.outside_height_mm','dimensions.outside_depth_mm','dimensions.fixed_shelf_count'}


def normalize_request(text):
    if not isinstance(text,str) or not text.strip() or len(text)>4000:raise StoreError(422,'PROPOSAL_TEXT_INVALID','Enter 1 to 4,000 characters.','text')
    return ' '.join(unicodedata.normalize('NFKC',text).split())


class FakeProvider:
    provider_id='offline_demo'
    model_id='deterministic_fake_v1'
    def propose(self,text,base_revision_id):
        lower=text.lower()
        response={'schema_version':'1.0.0','base_revision_id':base_revision_id,'intent':'update','template_id':'plywood_bookcase_v1','changes':[],'questions':[],'explanation':'Offline deterministic demo. Review the proposed changes before applying.'}
        if 'timeout' in lower:raise TimeoutError('Synthetic provider timeout.')
        if 'malformed' in lower:return '{invalid json'
        if re.search(r'\b(?:drawers?|chairs?|tables?|doors?)\b',lower):
            response.update(intent='unsupported',explanation='This release supports an open-front plywood bookcase with fixed shelves and an applied back.')
        elif 'thickness' in lower:
            response.update(intent='clarify',questions=[{'field':'materials.main.actual_thickness_mm','question':'What is the actual measured panel thickness? Enter it in the material form.'}],explanation='Measured thickness is supplied through the ordinary material form.')
        else:
            token=r'([+\-−]?\s*[0-9][0-9./]*(?:\s+[0-9]+/[0-9]+)?\s*(?:inches|inch|in|mm|cm))'
            match=re.search(r'(?:(?:width|wide)\s*(?:to|of|=)?\s*|(?:make it|make this)\s*)'+token,lower)
            if match is None:match=re.search(r'(?<![\w.+/\-−])'+token+r'\s*(?:wide|width)',lower)
            if match:
                measurement=re.sub(r'\binch(?:es)?\b','in',match[1])
                response['changes']=[{'field':'dimensions.outside_width_mm','value_mm':normalize_measurement(measurement,field='dimensions.outside_width_mm')}]
            else:
                response.update(intent='clarify',questions=[{'field':'dimensions.outside_width_mm','question':'What outside width would you like, including units?'}],explanation='The offline demo recognizes width edits; other measurements remain in the forms.')
        return json.dumps(response)


def validate_proposal(raw,base):
    if not isinstance(raw,(str,dict)):raise ValueError('Proposal must be JSON data.')
    if isinstance(raw,str):
        if len(raw.encode('utf-8'))>32*1024:raise ValueError('Provider response exceeds limit.')
        value=json.loads(raw)
    else:value=deepcopy(raw)
    jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text())).validate(value)
    if value['base_revision_id']!=base['id']:raise StoreError(409,'STALE_PROPOSAL_BASE','The provider response used a different base revision.')
    fields=[c['field'] for c in value['changes']]
    if len(fields)!=len(set(fields)) or not set(fields)<=ALLOWED:raise ValueError('Duplicate or unsupported proposal fields.')
    if value['intent']=='update' and not fields and not value['questions']:raise ValueError('An update requires changes or unresolved questions.')
    applicable=value['intent']=='update' and bool(fields) and not value['questions']
    spec=deepcopy(base['spec'])
    for change in value['changes']:
        field=change['field'].split('.')[1]
        spec['dimensions'][field]=change.get('value_mm',change.get('value_count'))
    candidate=compile_design(spec)
    return {'response':value,'candidate_spec':candidate['spec'] if applicable else None,'diff':semantic_diff(base['resolved'],candidate) if fields else None,'applicable':applicable,'usage':None,'cost':None,'provider':'offline_demo','model':'deterministic_fake_v1'}


class ProposalService:
    def __init__(self,store,provider=None):
        self.store=store;self.provider=provider or FakeProvider()
    def request(self,project_id,base_revision_id,text,key,mode='fake'):
        text=normalize_request(text)
        if mode!='fake':raise StoreError(503,'AI_UNCONFIGURED','Live AI is not configured. Use the forms or the offline proposal demo.')
        if not isinstance(key,str) or not 1<=len(key)<=100:raise StoreError(422,'IDEMPOTENCY_KEY_INVALID','Supply an idempotency key.')
        request_hash=hash_json({'project_id':project_id,'base_revision_id':base_revision_id,'text':text,'provider':self.provider.provider_id,'model':self.provider.model_id})
        with self.store.transaction() as db:
            existing=db.execute('SELECT id,request_sha256 FROM proposals WHERE project_id=? AND idempotency_key=?',(project_id,key)).fetchone()
            if existing:
                if existing['request_sha256']!=request_hash:raise StoreError(409,'IDEMPOTENCY_CONFLICT','This proposal key belongs to different request content.')
                return self.store._row(db,'proposals',existing['id'])
            project=self.store._row(db,'projects',project_id)
            base=self.store._row(db,'revisions',base_revision_id)
            if base['project_id']!=project_id or project['latest_accepted_revision_id']!=base_revision_id:raise StoreError(409,'STALE_BASE_REVISION','Review the current project revision before requesting a proposal.')
            identifier=new_id('proposal')
            db.execute('INSERT INTO proposals(id,project_id,base_revision_id,idempotency_key,request_sha256,state,created_at) VALUES(?,?,?,?,?,?,?)',(identifier,project_id,base_revision_id,key,request_hash,'pending',now()))
        try:
            result=validate_proposal(self.provider.propose(text,base_revision_id),base)
            result['request_text']=text
            state,code='ready',None
        except TimeoutError:result=None;state,code='uncertain','PROVIDER_TIMEOUT'
        except StoreError as error:result=None;state,code='failed',error.code
        except (ValueError,KeyError,jsonschema.ValidationError):result=None;state,code='failed','PROPOSAL_INVALID'
        except Exception:result=None;state,code='uncertain','PROVIDER_FAILED'
        with self.store.transaction() as db:
            db.execute("UPDATE proposals SET state=?,proposal_json=?,diagnostic_code=? WHERE id=? AND state='pending'",(state,canonical_json(result) if result else None,code,identifier))
            return self.store._row(db,'proposals',identifier)
    def get(self,identifier):
        with self.store.connection() as db:
            value=self.store._row(db,'proposals',identifier)
            project=self.store._row(db,'projects',value['project_id'])
        value['stale']=project['latest_accepted_revision_id']!=value['base_revision_id'] and value['applied_revision_id'] is None
        return value
    def apply(self,identifier,expected_base_revision_id):
        with self.store.transaction() as db:
            proposal=self.store._row(db,'proposals',identifier)
            if expected_base_revision_id!=proposal['base_revision_id']:raise StoreError(409,'BASE_REVISION_MISMATCH','The apply request used a different base revision.')
            if proposal['applied_revision_id']:
                return {'revision':self.store._row(db,'revisions',proposal['applied_revision_id']),'already_applied':True}
            project=self.store._row(db,'projects',proposal['project_id'])
            if project['latest_accepted_revision_id']!=proposal['base_revision_id']:raise StoreError(409,'STALE_BASE_REVISION','The project changed. Request and review a fresh proposal.')
            if proposal['state']!='ready' or not proposal['proposal']['applicable']:raise StoreError(409,'PROPOSAL_NOT_APPLICABLE','Resolve the proposal questions before applying.')
            base=self.store._row(db,'revisions',proposal['base_revision_id'])
            # Validate again at consumption; provider data never bypasses normal compilation.
            checked=validate_proposal(proposal['proposal']['response'],base)
            resolved=compile_design(checked['candidate_spec'])
            revision=self.store._insert_revision(db,project['id'],resolved['spec'],resolved,base['number']+1,base['id'])
            db.execute("UPDATE proposals SET state='applied',applied_revision_id=? WHERE id=?",(revision['id'],identifier))
            db.execute('DELETE FROM drafts WHERE project_id=?',(project['id'],))
            return {'revision':revision,'diff':semantic_diff(base['resolved'],resolved),'already_applied':False}
