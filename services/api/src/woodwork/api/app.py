from contextlib import asynccontextmanager
import importlib.util
import json
import os
from pathlib import Path
import secrets
from urllib.parse import urlsplit

from fastapi import FastAPI,Request,Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse,FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from woodwork import __version__
from woodwork.application import compile_design,installed_recipes
from woodwork.domain import DomainError,ProjectSpec,normalize_measurement,MODELING_BOUNDS
from woodwork.exports.core import sha256_file
from woodwork.jobs.dispatcher import Dispatcher
from woodwork.runtime import runtime_versions
from woodwork.storage import Store,StoreError
from woodwork.storage.paths import contained_file
from woodwork.templates import default_project_spec
from .models import CreateProject,CreateRevision,Draft,Empty,JobRequest,PackageRequest,Measurement,ImportRequest,ProposalRequest,ApplyProposal


class ApplicationFiles(StaticFiles):
    """Revalidate the HTML shell so local updates load their new hashed bundle."""
    async def get_response(self,path,scope):
        response=await super().get_response(path,scope)
        if path in {'','.','/'} or path.lower().endswith('.html'):
            response.headers['Cache-Control']='no-cache'
        return response
PREFIX='/api/v1'
JSON_LIMIT=256*1024

def default_data_root():
    default=Path.home()/'AppData/Local/WoodworkingPlanner/data' if os.name=='nt' else Path.home()/'.local/share/woodworking-planner'
    return Path(os.environ.get('WOODWORK_DATA_ROOT',str(default))).resolve()

def error_response(status,code,message,field=None,details=None):
    return JSONResponse({'error':{'code':code,'message':message,'field':field,'details':details or {}}},status_code=status)

class LocalBoundary(BaseHTTPMiddleware):
    async def dispatch(self,request,call_next):
        try:host=urlsplit('//'+request.headers.get('host','')).hostname
        except ValueError:host=None
        if host not in request.app.state.allowed_hosts:return error_response(403,'LOCAL_HOST_REJECTED','This application accepts trusted local hosts only.')
        if request.method in {'POST','PUT','PATCH','DELETE'}:
            origin=request.headers.get('origin')
            if origin and origin not in request.app.state.allowed_origins:return error_response(403,'LOCAL_ORIGIN_REJECTED','Requests from another origin cannot change local projects.')
            token=request.headers.get('x-woodwork-csrf','')
            if not secrets.compare_digest(token,request.app.state.csrf_token):return error_response(403,'CSRF_REQUIRED','Refresh the local application session before changing a project.')
            limit=32*1024*1024 if request.url.path==PREFIX+'/imports/validate' else JSON_LIMIT
            length=request.headers.get('content-length')
            try:
                if length is not None and (int(length)<0 or int(length)>limit):return error_response(413,'INPUT_TOO_LARGE','Request exceeds the input size limit.')
            except ValueError:return error_response(400,'CONTENT_LENGTH_INVALID','Invalid request length.')
            total=0
            pieces=[]
            async for piece in request.stream():
                total+=len(piece)
                if total>limit:return error_response(413,'INPUT_TOO_LARGE','Request exceeds the input size limit.')
                pieces.append(piece)
            request._body=b''.join(pieces)
        return await call_next(request)

def create_app(data_root=None,*,start_dispatcher=True,testing=False):
    root=Path(data_root).resolve() if data_root is not None else default_data_root()
    store=Store(root)
    dispatcher=Dispatcher(store,cad_timeout=float(os.environ.get('WOODWORK_CAD_TIMEOUT','120')),export_timeout=float(os.environ.get('WOODWORK_EXPORT_TIMEOUT','120')))
    @asynccontextmanager
    async def lifespan(app):
        if start_dispatcher:dispatcher.start()
        try:yield
        finally:dispatcher.close()
    app=FastAPI(title='Woodworking Planner',version=__version__,lifespan=lifespan)
    app.state.store=store
    from woodwork.proposals import ProposalService
    proposals=ProposalService(store)
    app.state.dispatcher=dispatcher
    app.state.csrf_token=secrets.token_urlsafe(32)
    app.state.runtime=runtime_versions()
    app.state.allowed_hosts={'localhost','127.0.0.1','::1'}|({'testserver'} if testing else set())
    app.state.allowed_origins={'http://localhost:8777','http://127.0.0.1:8777','http://localhost:5173','http://127.0.0.1:5173'}|({'http://testserver'} if testing else set())
    app.add_middleware(LocalBoundary)
    app.add_middleware(CORSMiddleware,allow_origins=list(app.state.allowed_origins),allow_methods=['GET','POST','PUT'],allow_headers=['Content-Type','X-Woodwork-CSRF'],allow_credentials=True)
    @app.exception_handler(StoreError)
    async def store_error(request,error):return error_response(error.status,error.code,error.message,error.field,error.details)
    @app.exception_handler(DomainError)
    async def domain_error(request,error):
        first=error.findings[0]
        return error_response(422,first['code'],first['message'],first.get('field'),{'findings':error.findings})
    @app.exception_handler(RequestValidationError)
    async def request_error(request,error):
        errors=error.errors()
        if any(e['type']=='json_invalid' for e in errors):return error_response(400,'JSON_INVALID','Malformed JSON request.')
        findings=[{'code':'SCHEMA_INVALID','message':e['msg'],'field':'.'.join(str(p) for p in e['loc'] if p not in ('body','spec')),'details':{}} for e in errors]
        return error_response(422,'SCHEMA_INVALID','Check the highlighted request fields.',details={'findings':findings})
    @app.exception_handler(Exception)
    async def unexpected_error(request,error):return error_response(500,'OPERATION_FAILED','The local operation failed. Existing project revisions were preserved.')

    @app.get(PREFIX+'/health')
    def health():return {'status':'ready','schema_version':'1.0.0','database_version':2,'app_version':__version__}
    @app.get(PREFIX+'/ai/status')
    def ai_status():return {'live':'unconfigured','default':'disabled','offline_demo':'available','credentials_required_for_forms':False}
    @app.post(PREFIX+'/projects/{project_id}/proposals',status_code=202)
    def request_proposal(project_id:str,body:ProposalRequest):return {'proposal':proposals.request(project_id,body.base_revision_id,body.text,body.idempotency_key,body.mode)}
    @app.get(PREFIX+'/proposals/{proposal_id}')
    def get_proposal(proposal_id:str):return {'proposal':proposals.get(proposal_id)}
    @app.post(PREFIX+'/proposals/{proposal_id}/apply')
    def apply_proposal(proposal_id:str,body:ApplyProposal):return proposals.apply(proposal_id,body.expected_base_revision_id)
    @app.get(PREFIX+'/session')
    def session():
        response=JSONResponse({'csrf_token':app.state.csrf_token})
        response.set_cookie('woodwork_session',app.state.csrf_token,httponly=True,samesite='strict')
        return response
    @app.get(PREFIX+'/runtime')
    def runtime():
        path=root/'runtime-preflight.json'
        last=None
        if path.is_file():
            try:last=json.loads(path.read_text(encoding='utf-8'))
            except (ValueError,OSError):pass
        return {**app.state.runtime,'data_root':str(root),'application_root':str(Path(__file__).resolve().parents[5]),'last_preflight':last,'status':'unavailable' if app.state.runtime['missing_components'] else ('ready' if last and last.get('status')=='passed' else 'preflight_available')}
    @app.post(PREFIX+'/runtime/preflight',status_code=202)
    def preflight(body:Empty):
        job=store.queue_preflight();dispatcher.notify();return {'job':job}
    @app.get(PREFIX+'/templates')
    def templates():
        recipes=[{'id':identifier,'version':version,'title':entry.get('title',identifier),'required_tools':entry.get('required_tools',[])} for (identifier,version),entry in installed_recipes().items() if not entry.get('test_only')]
        return {'templates':[{'id':'plywood_bookcase_v1','version':'1.0.0','default_spec':default_project_spec(),'bounds':MODELING_BOUNDS,'recipes':recipes}]}
    @app.post(PREFIX+'/inputs/normalize')
    def normalize(body:list[Measurement]):
        if len(body)>40:raise StoreError(422,'TOO_MANY_INPUTS','Normalize at most 40 fields at a time.')
        values=[];errors=[]
        for item in body:
            try:values.append({'field':item.field,'value_mm':normalize_measurement(item.text,item.default_unit,field=item.field)})
            except DomainError as error:errors.extend(error.findings)
        if errors:return JSONResponse({'values':values,'errors':errors,'error':{'code':'MEASUREMENT_INVALID','message':'Check the highlighted measurements.','field':None,'details':{'findings':errors}}},status_code=422)
        return {'values':values,'errors':[]}
    @app.post(PREFIX+'/specs/validate')
    def validate(body:ProjectSpec):
        resolved=compile_design(body)
        return {'spec':resolved['spec'],'resolved':resolved,'summary':{'inside_width_mm':resolved['inside_width_mm'],'carcass_depth_mm':resolved['carcass_depth_mm'],'clear_height_mm':resolved['rounded_clear_height_target_mm'],'opening_count':len(resolved['openings']),'part_count':resolved['part_instance_count']}}
    @app.get(PREFIX+'/projects')
    def projects(limit:int=Query(50,ge=1,le=100),offset:int=Query(0,ge=0)):return {'projects':store.list_projects(limit,offset)}
    @app.post(PREFIX+'/projects',status_code=201)
    def create_project(body:CreateProject):return store.create_project(body.title,body.spec)
    @app.get(PREFIX+'/projects/{project_id}')
    def project(project_id:str):return {'project':store.get_project(project_id),'draft':store.get_draft(project_id)}
    @app.put(PREFIX+'/projects/{project_id}/draft')
    def draft(project_id:str,body:Draft):return store.save_draft(project_id,body.base_revision_id,body.raw)
    @app.post(PREFIX+'/projects/{project_id}/revisions',status_code=201)
    def revision(project_id:str,body:CreateRevision):return store.create_revision(project_id,body.base_revision_id,body.spec)
    @app.get(PREFIX+'/projects/{project_id}/revisions')
    def revisions(project_id:str,limit:int=Query(50,ge=1,le=100),offset:int=Query(0,ge=0)):return {'revisions':store.list_revisions(project_id,limit,offset)}
    @app.get(PREFIX+'/revisions/{revision_id}')
    def revision_detail(revision_id:str):return {'revision':store.get_revision(revision_id),'artifact_set_ids':store.list_artifact_sets(revision_id),'jobs':store.list_jobs(revision_id)}
    @app.post(PREFIX+'/revisions/{revision_id}/jobs',status_code=202)
    def create_job(revision_id:str,body:JobRequest):
        if app.state.runtime['missing_components']:raise StoreError(503,'RUNTIME_UNAVAILABLE','Install the locked runtime and run preflight.')
        if body.kind!='generate' and importlib.util.find_spec('woodwork.exports.'+('documents' if body.kind=='documents' else 'stock')) is None:raise StoreError(503,'CAPABILITY_UNAVAILABLE','This output capability is not installed.')
        job=store.queue_job(revision_id,body.kind,body.idempotency_key,source_artifact_set_id=body.source_artifact_set_id)
        dispatcher.notify();return {'job':job}
    @app.get(PREFIX+'/jobs/{job_id}')
    def job(job_id:str):return {'job':store.get_job(job_id)}
    @app.post(PREFIX+'/jobs/{job_id}/cancel')
    def cancel(job_id:str,body:Empty):return {'job':dispatcher.cancel(job_id)}
    @app.get(PREFIX+'/revisions/{revision_id}/manifest')
    def manifest(revision_id:str,artifact_set_id:str|None=Query(None,max_length=100)):
        revision=store.get_revision(revision_id)
        selected=artifact_set_id or revision['preferred_artifact_set_id']
        if selected is None:raise StoreError(409,'GEOMETRY_REQUIRED','This revision has no completed artifact set yet.')
        record=store.get_artifact_set(selected)
        if record['revision_id']!=revision_id:raise StoreError(409,'ARTIFACT_SET_MISMATCH','The requested artifact set belongs to another revision.')
        path=contained_file(root,record['relative_dir']+'/manifest.json')
        if sha256_file(path)!=record['manifest_sha256']:raise StoreError(409,'ARTIFACT_INTEGRITY_FAILED','The saved manifest has changed. Regenerate this revision.')
        from woodwork.cad_adapter import validate_artifact_set
        try:validate_artifact_set(path.parent,inspect_geometry=False)
        except (ValueError,OSError,KeyError):raise StoreError(409,'ARTIFACT_INTEGRITY_FAILED','A saved artifact is missing or changed. Regenerate this revision.') from None
        return {'artifact_set_id':selected,'manifest':json.loads(path.read_text(encoding='utf-8'))}
    @app.get(PREFIX+'/artifacts/{artifact_id}/download')
    def download(artifact_id:str):
        artifact=store.get_artifact(artifact_id)
        record=artifact['record'];source=store.get_artifact_set(artifact['artifact_set_id'])
        directory=artifact.get('relative_dir',source['relative_dir'])
        path=contained_file(root,directory+'/'+record['relative_path'])
        if path.stat().st_size!=record['size_bytes'] or sha256_file(path)!=record['sha256']:raise StoreError(409,'ARTIFACT_INTEGRITY_FAILED','The saved artifact has changed. Regenerate this revision.')
        return FileResponse(path,media_type=record['mime_type'],filename=Path(record['relative_path']).name)
    @app.post(PREFIX+'/revisions/{revision_id}/package',status_code=202)
    def package(revision_id:str,body:PackageRequest):
        if importlib.util.find_spec('woodwork.exports.package') is None:raise StoreError(503,'CAPABILITY_UNAVAILABLE','Portable package output is not installed.')
        job=store.queue_job(revision_id,'package',body.idempotency_key,source_artifact_set_id=body.artifact_set_id)
        dispatcher.notify();return {'job':job}
    @app.post(PREFIX+'/imports/validate')
    async def validate_import(request:Request):
        from woodwork.imports import inspect_import
        from starlette.concurrency import run_in_threadpool
        return await run_in_threadpool(inspect_import,await request.body(),root)
    @app.post(PREFIX+'/imports',status_code=201)
    def import_project(body:ImportRequest):
        from woodwork.imports import accept_import
        return accept_import(store,body.token,body.title)
    dist=Path(__file__).resolve().parents[5]/'apps/web/dist'
    if dist.is_dir():app.mount('/',ApplicationFiles(directory=dist,html=True),name='web')
    return app
