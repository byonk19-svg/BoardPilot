"""Short SQLite transactions; native workers never update these pointers."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import uuid

from woodwork.domain import canonical_json, hash_json
from woodwork.application import compile_design as compile_project
from .schema import SCHEMA

TERMINAL = {'succeeded','failed','cancelled','interrupted'}

def now():
    return datetime.now(timezone.utc).isoformat()

def new_id(prefix):
    return prefix+'_'+uuid.uuid4().hex

class StoreError(ValueError):
    def __init__(self,status,code,message,field=None,details=None):
        self.status=status
        self.code=code
        self.message=message
        self.field=field
        self.details=details or {}
        super().__init__(message)

def semantic_diff(before,after):
    old={p['definition_id']:p for p in before['part_definitions']}
    new={p['definition_id']:p for p in after['part_definitions']}
    parts={key:{'before':old[key]['finished_mm'],'after':value['finished_mm'],'quantity_before':old[key]['quantity'],'quantity_after':value['quantity']} for key,value in new.items() if value['finished_mm']!=old[key]['finished_mm'] or value['quantity']!=old[key]['quantity']}
    return {'dimensions':{'before':before['spec']['dimensions'],'after':after['spec']['dimensions']},'parts':parts,'openings':{'before':before['openings'],'after':after['openings']},'materials_changed':before['spec']['materials']!=after['spec']['materials'],'construction':{'before':before['construction_status'],'after':after['construction_status']},'stock_layout_invalidated':before['spec']!=after['spec']}

class Store:
    def __init__(self,root,*,recipe_catalog=None):
        self.root=Path(root).resolve()
        self.root.mkdir(parents=True,exist_ok=True)
        self.path=self.root/'woodworking.sqlite3'
        self.recipe_catalog=recipe_catalog
        with self.connection() as db:
            current=db.execute('PRAGMA user_version').fetchone()[0]
            if current>2:raise StoreError(503,'DATABASE_VERSION_UNSUPPORTED','The project store needs a newer application version.')
            if current==0:
                try:db.executescript('BEGIN IMMEDIATE;'+SCHEMA+'COMMIT;')
                except Exception:
                    if db.in_transaction:db.rollback()
                    raise
            elif current==1:
                backup=self.root/('migration-v1-'+uuid.uuid4().hex+'.sqlite3')
                with sqlite3.connect(backup) as target:db.backup(target)
                try:db.executescript('BEGIN IMMEDIATE;CREATE TABLE exports (id TEXT PRIMARY KEY,artifact_set_id TEXT NOT NULL REFERENCES artifact_sets(id),relative_dir TEXT NOT NULL UNIQUE,record_json TEXT NOT NULL,created_at TEXT NOT NULL);PRAGMA user_version=2;COMMIT;')
                except Exception:
                    if db.in_transaction:db.rollback()
                    raise

    @contextmanager
    def connection(self):
        db=sqlite3.connect(self.path,timeout=10,isolation_level=None)
        db.row_factory=sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA journal_mode=WAL')
        try:yield db
        finally:db.close()

    @contextmanager
    def transaction(self):
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise

    def _row(self,db,table,identifier):
        if table not in {'projects','revisions','jobs','artifact_sets','artifacts','proposals','exports'}:raise ValueError('Unknown internal table')
        row=db.execute(f'SELECT * FROM {table} WHERE id=?',(identifier,)).fetchone()
        if row is None:raise StoreError(404,'NOT_FOUND','The requested record was not found.')
        value=dict(row)
        for key in list(value):
            if key.endswith('_json'):
                raw=value.pop(key)
                value[key[:-5]]=json.loads(raw) if raw is not None else None
        return value

    def get_project(self,project_id):
        with self.connection() as db:return self._row(db,'projects',project_id)

    def get_revision(self,revision_id):
        with self.connection() as db:return self._row(db,'revisions',revision_id)

    def get_job(self,job_id):
        with self.connection() as db:return self._row(db,'jobs',job_id)

    def get_artifact_set(self,set_id):
        with self.connection() as db:return self._row(db,'artifact_sets',set_id)

    def get_artifact(self,artifact_id):
        with self.connection() as db:
            if db.execute('SELECT 1 FROM artifacts WHERE id=?',(artifact_id,)).fetchone():return self._row(db,'artifacts',artifact_id)
            return self._row(db,'exports',artifact_id)

    def publish_package(self,job_id,record,relative_dir,metrics=None):
        with self.transaction() as db:
            job=self._row(db,'jobs',job_id)
            if job['state']=='succeeded':return self._row(db,'exports',job['result_artifact_id'])
            if job['kind']!='package' or job['state'] not in {'running','interrupted'}:raise StoreError(409,'JOB_NOT_PUBLISHABLE','This job cannot publish a package.')
            source=self._row(db,'artifact_sets',job['source_artifact_set_id'])
            if record['artifact_set_id']!=source['id'] or record['revision_id']!=job['revision_id'] or record['manifest_sha256']!=source['manifest_sha256']:raise StoreError(409,'SOURCE_BINDING_MISMATCH','Package source differs from the frozen set.')
            identifier=record['artifact_id']
            db.execute('INSERT INTO exports VALUES(?,?,?,?,?)',(identifier,source['id'],relative_dir,canonical_json(record),now()))
            db.execute("UPDATE jobs SET state='succeeded',diagnostic_code=NULL,stage='publishing',result_artifact_id=?,finished_at=?,metrics_json=? WHERE id=?",(identifier,now(),canonical_json(metrics) if metrics else None,job_id))
            return self._row(db,'exports',identifier)

    def list_projects(self,limit=50,offset=0):
        with self.connection() as db:
            return [self._row(db,'projects',r['id']) for r in db.execute('SELECT id FROM projects ORDER BY updated_at DESC LIMIT ? OFFSET ?',(min(limit,100),max(offset,0))).fetchall()]

    def list_revisions(self,project_id,limit=50,offset=0):
        with self.connection() as db:
            self._row(db,'projects',project_id)
            return [self._row(db,'revisions',r['id']) for r in db.execute('SELECT id FROM revisions WHERE project_id=? ORDER BY number DESC LIMIT ? OFFSET ?',(project_id,min(limit,100),max(offset,0))).fetchall()]

    def list_jobs(self,revision_id,limit=20):
        with self.connection() as db:
            return [self._row(db,'jobs',r['id']) for r in db.execute('SELECT id FROM jobs WHERE revision_id=? ORDER BY created_at DESC LIMIT ?',(revision_id,limit)).fetchall()]

    def list_artifact_sets(self,revision_id):
        with self.connection() as db:
            return [r['id'] for r in db.execute('SELECT id FROM artifact_sets WHERE revision_id=? ORDER BY created_at',(revision_id,)).fetchall()]

    def queue_preflight(self):
        with self.transaction() as db:
            existing=db.execute("SELECT id FROM jobs WHERE kind='preflight' AND state IN ('queued','running','cancelling') ORDER BY created_at LIMIT 1").fetchone()
            if existing:return self._row(db,'jobs',existing['id'])
            if db.execute("SELECT COUNT(*) FROM jobs WHERE state='queued'").fetchone()[0]>=10:raise StoreError(429,'QUEUE_FULL','The local queue is full.')
            identifier=new_id('job')
            db.execute('INSERT INTO jobs(id,revision_id,kind,state,stage,attempt,idempotency_key,request_sha256,created_at) VALUES(?,NULL,?,?,?,?,?,?,?)',(identifier,'preflight','queued','validating',1,identifier,hash_json({'preflight':identifier}),now()))
            return self._row(db,'jobs',identifier)

    def _insert_revision(self,db,project_id,spec,resolved,number,parent_id):
        identifier=new_id('rev')
        db.execute('INSERT INTO revisions(id,project_id,number,parent_id,spec_json,resolved_json,spec_sha256,resolved_sha256,created_at) VALUES(?,?,?,?,?,?,?,?,?)',(identifier,project_id,number,parent_id,canonical_json(spec),canonical_json(resolved),resolved['spec_sha256'],resolved['resolved_sha256'],now()))
        db.execute('UPDATE projects SET latest_accepted_revision_id=?,updated_at=? WHERE id=?',(identifier,now(),project_id))
        return self._row(db,'revisions',identifier)

    def create_project(self,title,spec,*,provenance=None):
        if not isinstance(title,str) or not title.strip() or len(title)>100:raise StoreError(422,'TITLE_INVALID','Enter a project name of 1 to 100 characters.','title')
        resolved=compile_project(spec,recipe_catalog=self.recipe_catalog)
        spec=resolved['spec']
        project_id=new_id('project')
        with self.transaction() as db:
            timestamp=now()
            db.execute('INSERT INTO projects(id,title,created_at,updated_at,provenance_json) VALUES(?,?,?,?,?)',(project_id,title.strip(),timestamp,timestamp,canonical_json(provenance) if provenance else None))
            revision=self._insert_revision(db,project_id,spec,resolved,1,None)
            return {'project':self._row(db,'projects',project_id),'revision':revision}

    def create_revision(self,project_id,base_revision_id,spec):
        before=self.get_revision(base_revision_id)
        if before['project_id']!=project_id:raise StoreError(409,'BASE_REVISION_MISMATCH','The base revision belongs to another project.')
        resolved=compile_project(spec,recipe_catalog=self.recipe_catalog)
        diff=semantic_diff(before['resolved'],resolved)
        with self.transaction() as db:
            project=self._row(db,'projects',project_id)
            if project['latest_accepted_revision_id']!=base_revision_id:raise StoreError(409,'STALE_BASE_REVISION','The project changed. Review the latest revision before applying this draft.')
            revision=self._insert_revision(db,project_id,resolved['spec'],resolved,before['number']+1,base_revision_id)
            db.execute('DELETE FROM drafts WHERE project_id=?',(project_id,))
            return {'revision':revision,'diff':diff}

    def save_draft(self,project_id,base_revision_id,raw):
        if len(canonical_json(raw).encode('utf-8'))>256*1024:raise StoreError(413,'DRAFT_TOO_LARGE','Draft exceeds the input limit.')
        with self.transaction() as db:
            project=self._row(db,'projects',project_id)
            base=self._row(db,'revisions',base_revision_id)
            if base['project_id']!=project_id or project['latest_accepted_revision_id']!=base_revision_id:raise StoreError(409,'STALE_BASE_REVISION','The draft is based on an older project revision.')
            db.execute('INSERT INTO drafts VALUES(?,?,?,?) ON CONFLICT(project_id) DO UPDATE SET base_revision_id=excluded.base_revision_id,raw_json=excluded.raw_json,updated_at=excluded.updated_at',(project_id,base_revision_id,canonical_json(raw),now()))
        return {'base_revision_id':base_revision_id,'raw':raw}

    def get_draft(self,project_id):
        with self.connection() as db:
            row=db.execute('SELECT * FROM drafts WHERE project_id=?',(project_id,)).fetchone()
            return {'base_revision_id':row['base_revision_id'],'raw':json.loads(row['raw_json']),'updated_at':row['updated_at']} if row else None

    def queue_job(self,revision_id,kind,idempotency_key,*,source_artifact_set_id=None):
        if kind not in {'generate','documents','stock','package'}:raise StoreError(422,'JOB_KIND_UNSUPPORTED','Choose a supported job kind.','kind')
        if not isinstance(idempotency_key,str) or not 1<=len(idempotency_key)<=100:raise StoreError(422,'IDEMPOTENCY_KEY_INVALID','Supply an idempotency key of 1 to 100 characters.')
        with self.transaction() as db:
            revision=self._row(db,'revisions',revision_id)
            source=source_artifact_set_id
            request_hash=hash_json({'revision_id':revision_id,'kind':kind,'source_artifact_set_id':source})
            existing=db.execute('SELECT id,request_sha256 FROM jobs WHERE revision_id=? AND kind=? AND idempotency_key=?',(revision_id,kind,idempotency_key)).fetchone()
            if existing:
                if existing['request_sha256']!=request_hash:raise StoreError(409,'IDEMPOTENCY_CONFLICT','This idempotency key already belongs to different request content.')
                return self._row(db,'jobs',existing['id'])
            if kind=='package' and source is None:source=revision['preferred_artifact_set_id']
            if kind=='generate' and source is not None:raise StoreError(422,'SOURCE_NOT_ALLOWED','Generation uses the immutable project specification.')
            if kind!='generate':
                if source is None:raise StoreError(409,'GEOMETRY_REQUIRED','Generate and verify this revision before requesting derived outputs.')
                source_set=self._row(db,'artifact_sets',source)
                if source_set['revision_id']!=revision_id or 'geometry' not in source_set['capabilities']:raise StoreError(409,'ARTIFACT_SET_MISMATCH','The selected source set belongs to another revision or lacks verified geometry.')
            if db.execute("SELECT COUNT(*) FROM jobs WHERE state='queued'").fetchone()[0]>=10:raise StoreError(429,'QUEUE_FULL','The local queue is full. Let current jobs finish or cancel queued work.')
            attempt=db.execute('SELECT COUNT(*) FROM jobs WHERE revision_id=? AND kind=?',(revision_id,kind)).fetchone()[0]+1
            identifier=new_id('job')
            db.execute('INSERT INTO jobs(id,revision_id,kind,state,stage,attempt,idempotency_key,request_sha256,source_artifact_set_id,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',(identifier,revision_id,kind,'queued','validating',attempt,idempotency_key,request_hash,source,now()))
            return self._row(db,'jobs',identifier)

    def claim_job(self,session):
        with self.transaction() as db:
            if db.execute("SELECT 1 FROM jobs WHERE state IN ('running','cancelling') LIMIT 1").fetchone():return None
            row=db.execute("SELECT id FROM jobs WHERE state='queued' ORDER BY created_at LIMIT 1").fetchone()
            if not row:return None
            db.execute("UPDATE jobs SET state='running',owner_session=?,started_at=? WHERE id=?",(session,now(),row['id']))
            return self._row(db,'jobs',row['id'])

    def update_stage(self,job_id,stage):
        if stage not in {'validating','compiling','generating_geometry','generating_side_panels','generating_horizontal_panels','generating_back_panel','assembling_geometry','inspecting_geometry','verifying_artifacts','generating_documents','planning_stock','packaging','publishing'}:return
        with self.transaction() as db:db.execute("UPDATE jobs SET stage=? WHERE id=? AND state='running'",(stage,job_id))

    def finish_job(self,job_id,state,code=None,metrics=None,result_artifact_id=None):
        if state not in TERMINAL:raise ValueError('Expected terminal job state')
        with self.transaction() as db:
            job=self._row(db,'jobs',job_id)
            if job['state'] in TERMINAL:return job
            db.execute('UPDATE jobs SET state=?,diagnostic_code=?,finished_at=?,metrics_json=?,result_artifact_id=? WHERE id=?',(state,code,now(),canonical_json(metrics) if metrics else None,result_artifact_id,job_id))
            return self._row(db,'jobs',job_id)

    def cancel_job(self,job_id):
        with self.transaction() as db:
            job=self._row(db,'jobs',job_id)
            if job['state'] in TERMINAL:return job
            state='cancelled' if job['state']=='queued' else 'cancelling'
            db.execute('UPDATE jobs SET state=?,finished_at=? WHERE id=?',(state,now() if state=='cancelled' else None,job_id))
            return self._row(db,'jobs',job_id)

    def recover_interrupted_jobs(self):
        with self.transaction() as db:
            rows=db.execute("SELECT id FROM jobs WHERE state IN ('running','cancelling')").fetchall()
            db.execute("UPDATE jobs SET state='interrupted',diagnostic_code='COORDINATOR_INTERRUPTED',finished_at=? WHERE state='running'",(now(),))
            db.execute("UPDATE jobs SET state='cancelled',diagnostic_code='CANCELLED_ON_RESTART',finished_at=? WHERE state='cancelling'",(now(),))
            return [r['id'] for r in rows]

    def publish_result(self,job_id,manifest,relative_dir,manifest_sha256,metrics=None):
        # The sole dispatcher has already independently verified bytes and schema.
        if Path(relative_dir).is_absolute() or '..' in Path(relative_dir).parts:raise StoreError(422,'ARTIFACT_PATH_INVALID','Invalid application-owned artifact location.')
        with self.transaction() as db:
            job=self._row(db,'jobs',job_id)
            revision=self._row(db,'revisions',job['revision_id'])
            if job['state']=='succeeded':return self._row(db,'artifact_sets',job['result_artifact_set_id'])
            if job['state'] not in {'running','interrupted'}:raise StoreError(409,'JOB_NOT_PUBLISHABLE','Only a completed owned worker or verified recovery can publish a result.')
            if manifest['revision_id']!=revision['id'] or manifest['project_id']!=revision['project_id'] or manifest['spec_sha256']!=revision['spec_sha256'] or manifest['resolved_sha256']!=revision['resolved_sha256']:raise StoreError(409,'REVISION_BINDING_MISMATCH','The result does not describe the job revision.')
            if manifest['source_artifact_set_id']!=job['source_artifact_set_id']:raise StoreError(409,'SOURCE_BINDING_MISMATCH','The result uses a different frozen source set.')
            required={'generate':'geometry','documents':'documents','stock':'stock_layout'}.get(job['kind'])
            if required is None or required not in manifest['capabilities']:raise StoreError(409,'JOB_OUTPUT_INCOMPLETE','The output is missing the capability requested by this job.')
            identifier=manifest['artifact_set_id']
            db.execute('INSERT INTO artifact_sets VALUES(?,?,?,?,?,?,?,?)',(identifier,revision['id'],manifest['source_artifact_set_id'],relative_dir,manifest_sha256,canonical_json(manifest['capabilities']),canonical_json(manifest),now()))
            for artifact in manifest['artifacts']:
                if artifact['revision_id']!=revision['id'] or artifact['spec_sha256']!=revision['spec_sha256']:raise StoreError(409,'REVISION_BINDING_MISMATCH','An artifact uses a different revision.')
                db.execute('INSERT INTO artifacts VALUES(?,?,?)',(artifact['artifact_id'],identifier,canonical_json(artifact)))
            preferred=revision['preferred_artifact_set_id']
            current_caps=set(self._row(db,'artifact_sets',preferred)['capabilities']) if preferred else set()
            capabilities=set(manifest['capabilities'])
            if 'geometry' in capabilities and capabilities>=current_caps:
                db.execute('UPDATE revisions SET preferred_artifact_set_id=? WHERE id=?',(identifier,revision['id']))
                project=self._row(db,'projects',revision['project_id'])
                if project['latest_accepted_revision_id']==revision['id']:
                    db.execute('UPDATE projects SET latest_successful_revision_id=?,updated_at=? WHERE id=?',(revision['id'],now(),project['id']))
            db.execute("UPDATE jobs SET state='succeeded',diagnostic_code=NULL,stage='publishing',result_artifact_set_id=?,finished_at=?,metrics_json=? WHERE id=?",(identifier,now(),canonical_json(metrics) if metrics else None,job_id))
            return self._row(db,'artifact_sets',identifier)
