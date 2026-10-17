"""Actual API option-only exports, synthetic credential boundary and cache reopen.

The coordinator supplies a private synthetic marker and restarts the API first.
This diagnostic never configures a provider, prints environment values, changes
the original revision, or removes anything outside the exact disposable cache.
"""
import argparse
from copy import deepcopy
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import time
from urllib.parse import urlparse
import uuid
import zipfile

import httpx
import psutil
from pypdf import PdfReader

from woodwork.cad_adapter import validate_artifact_set
from woodwork.domain import hash_json
from woodwork.exports.core import sha256_file, write_json
from woodwork.exports.package import verify_package
from woodwork.exports.stock import validate_stock_output
from woodwork.exports.documents import validate_documents


class DiagnosticError(ValueError):
    pass


def require(condition,message):
    if not condition:raise DiagnosticError(message)


def assert_only_change(before,after,path):
    prior=deepcopy(before);current=deepcopy(after)
    left,right=prior,current
    for key in path[:-1]:left,right=left[key],right[key]
    require(left[path[-1]]!=right[path[-1]],'The selected option did not change.')
    right[path[-1]]=left[path[-1]]
    require(prior==current,'An unrelated project field changed.')


def assert_same_geometry(before,after):
    for key in ('geometry_sha256','part_definitions','part_instances','world_aabb_mm','openings','total_part_volume_mm3'):
        require(before[key]==after[key],'Option-only change altered '+key+'.')


def linked(path):
    return path.is_symlink() or (hasattr(path,'is_junction') and path.is_junction())


def assert_unlinked(path,stop):
    for item in (path,*path.parents):
        require(not linked(item),'Filesystem link encountered; cache cleanup skipped.')
        if item==stop:return
    raise DiagnosticError('Path is outside the declared containment root.')


def cache_namespace(data_root,lock_file,appdata):
    root=Path(data_root).resolve();appdata=Path(appdata).resolve()
    require(root!=appdata and root.is_relative_to(appdata),'Data root is outside local app data.')
    name='cadgen-0.7.21-'+hashlib.sha256(Path(lock_file).read_bytes()).hexdigest()[:16]
    cache=root/'cache'/name
    assert_unlinked(cache,appdata)
    require(cache.resolve().parent==root/'cache','Unexpected cache namespace containment.')
    return cache


def recreate_cache(data_root,lock_file,appdata):
    cache=cache_namespace(data_root,lock_file,appdata)
    require(cache.is_dir(),'Expected generated CAD cache namespace is missing.')
    count=0
    for base,directories,files in os.walk(cache,followlinks=False):
        for name in (*directories,*files):
            path=Path(base)/name
            require(not linked(path),'Filesystem link encountered; cache cleanup skipped.')
            require(path.resolve().is_relative_to(cache),'Cache entry escapes namespace; cleanup skipped.')
            if path.is_file():count+=1
    # Recheck the exact resolved target immediately before native deletion.
    require(cache_namespace(data_root,lock_file,appdata)==cache,'Cache namespace changed.')
    shutil.rmtree(cache)
    cache.mkdir()
    return {'status':'passed','namespace':str(cache),'removed_disposable_files':count,'recreated_empty':not any(cache.iterdir())}


def scan_blob(data,marker,label,depth=0):
    require(bool(marker),'Private synthetic verification marker is missing.')
    require(marker not in data,'Synthetic credential detected in '+label+'.')
    checked=1
    if data.startswith(b'PK\x03\x04'):
        require(depth==0,'Unexpected nested ZIP in diagnostic output.')
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            require(sum(entry.file_size for entry in archive.infolist())<=256*1024*1024,'Diagnostic ZIP exceeds bounded scan size.')
            for entry in archive.infolist():
                require(entry.file_size<=64*1024*1024,'Diagnostic ZIP entry exceeds scan bound.')
                checked+=scan_blob(archive.read(entry),marker,label+'/'+entry.filename,depth+1)
    elif data.startswith(b'%PDF-'):
        reader=PdfReader(io.BytesIO(data))
        searchable=('\n'.join(page.extract_text() or '' for page in reader.pages)+str(reader.metadata)).encode('utf-8')
        require(marker not in searchable,'Synthetic credential detected in searchable PDF '+label+'.')
    return checked


def scan_paths(paths,marker):
    count=0
    for path in sorted(set(Path(p) for p in paths)):
        require(path.is_file() and not linked(path),'Untrusted path in credential scan.')
        count+=scan_blob(path.read_bytes(),marker,path.name)
    return count


class Probe:
    def __init__(self,client,root,output,api_pid,marker):
        self.client,self.root,self.output,self.api_pid,self.marker=client,root,output,api_pid,marker
        self.jobs=[];self.manifests=[];self.worker_environment_checks=[]

    def request(self,method,path,**kwargs):
        response=self.client.request(method,path,**kwargs)
        require(response.is_success,'Local API request failed ('+str(response.status_code)+'): '+path)
        return response.json()

    def revision(self,identifier):return self.request('GET','/revisions/'+identifier)['revision']

    def manifest(self,revision_id,set_id=None):
        params={'artifact_set_id':set_id} if set_id else {}
        result=self.request('GET','/revisions/'+revision_id+'/manifest',params=params)
        manifest=result['manifest']
        path=self.root/'artifacts'/manifest['artifact_set_id']
        require(path.resolve().is_relative_to(self.root/'artifacts'),'Manifest escapes artifact root.')
        assert_unlinked(path,self.root)
        require(json.loads((path/'manifest.json').read_text())==manifest,'API and saved manifest differ.')
        validate_artifact_set(path,inspect_geometry=False)
        return manifest,path

    def sample_environment(self,job):
        previous=next((item for item in self.worker_environment_checks if item['job_id']==job['id']),None)
        if previous and previous['descendants_sampled']>0:return
        target=(self.root/'jobs'/job['id']).resolve()
        for process in psutil.Process(self.api_pid).children(recursive=True):
            try:
                args=process.cmdline()
                if 'woodwork.jobs.worker' not in args or Path(args[-1]).resolve()!=target:continue
                environment=process.environ()
                require(not any(self.marker.decode() in value for value in environment.values()),'Synthetic credential reached an owned CAD worker environment.')
                require('OPENAI_API_KEY' not in environment and 'ANTHROPIC_API_KEY' not in environment,'Provider credential key reached an owned CAD worker.')
                descendants=process.children(recursive=True)
                inspected=0
                for child in descendants:
                    try:
                        require(not any(self.marker.decode() in value for value in child.environ().values()),'Synthetic credential reached an owned worker descendant.')
                        inspected+=1
                    except psutil.NoSuchProcess:continue
                report={'job_id':job['id'],'kind':job['kind'],'worker_pid':process.pid,'credential_absent':True,'descendants_sampled':inspected}
                if previous:previous.update(report)
                else:self.worker_environment_checks.append(report)
            except psutil.NoSuchProcess:continue

    def job(self,revision_id,kind,source=None):
        payload={'idempotency_key':'export-option-check-'+uuid.uuid4().hex}
        if kind=='package':
            path='/revisions/'+revision_id+'/package';payload['artifact_set_id']=source
        else:
            path='/revisions/'+revision_id+'/jobs';payload['kind']=kind
            if source:payload['source_artifact_set_id']=source
        job=self.request('POST',path,json=payload)['job']
        deadline=time.monotonic()+140
        last=None
        while time.monotonic()<deadline:
            job=self.request('GET','/jobs/'+job['id'])['job']
            self.sample_environment(job)
            if job['stage']!=last:
                print(json.dumps({'job_id':job['id'],'kind':kind,'stage':job['stage'],'state':job['state']}),flush=True);last=job['stage']
            if job['state'] in {'succeeded','failed','cancelled','interrupted'}:
                self.jobs.append(job)
                write_json(self.output/'jobs.json',self.jobs)
                require(job['state']=='succeeded','Native/export job ended '+job['state']+' ('+str(job['diagnostic_code'])+').')
                require(job['metrics']['elapsed_seconds']<=120,'Job exceeded the required 120 second profile.')
                if job.get('result_artifact_set_id'):
                    self.manifests.append(self.manifest(revision_id,job['result_artifact_set_id']))
                return job
            time.sleep(.3)
        raise DiagnosticError('Diagnostic job observation deadline exceeded.')

    def snapshot(self,revision_id):
        detail=self.request('GET','/revisions/'+revision_id)
        sets=[]
        for identifier in detail['artifact_set_ids']:
            manifest,path=self.manifest(revision_id,identifier)
            sets.append({'artifact_set_id':identifier,'manifest_sha256':sha256_file(path/'manifest.json'),'payload_sha256':{r['relative_path']:sha256_file(path/r['relative_path']) for r in manifest['artifacts']}})
        immutable={k:v for k,v in detail['revision'].items() if k!='preferred_artifact_set_id'}
        return {'revision':immutable,'artifact_sets':sets}

    def verify_revision_set(self,revision,kind):
        manifest,path=self.manifest(revision['id'])
        for key in ('project_id','revision_id','revision_number','spec_sha256','resolved_sha256'):
            expected={'project_id':revision['project_id'],'revision_id':revision['id'],'revision_number':revision['number'],'spec_sha256':revision['spec_sha256'],'resolved_sha256':revision['resolved_sha256']}[key]
            require(manifest[key]==expected,'Manifest revision identity mismatch: '+key)
        require(json.loads((path/'project.json').read_text())==revision['spec'],'Saved source spec mismatch.')
        require(json.loads((path/'resolved-project.json').read_text())==revision['resolved'],'Saved source ledger mismatch.')
        rows=list(csv.DictReader(io.StringIO((path/'cut-list.csv').read_text())))
        require(bool(rows) and all(row['revision_id']==revision['id'] and row['spec_sha256']==revision['spec_sha256'] for row in rows),'CSV source headers mismatch.')
        metadata={k:manifest[k] for k in ('project_id','revision_id','revision_number','spec_sha256','resolved_sha256','source_artifact_set_id')}
        report={'kind':kind,'revision_id':revision['id'],'revision_number':revision['number'],'artifact_set_id':manifest['artifact_set_id'],'spec_sha256':revision['spec_sha256'],'resolved_sha256':revision['resolved_sha256'],'manifest_sha256':sha256_file(path/'manifest.json'),'files':{r['relative_path']:r['sha256'] for r in manifest['artifacts']}}
        if 'stock_layout' in manifest['capabilities']:
            report['stock']=validate_stock_output(path,revision['spec'],revision['resolved'],metadata)
            plan=json.loads((path/'stock-layout.json').read_text())['plan']
            kerf=revision['spec']['manufacturing']['saw_kerf_mm']
            require(all(cut['kerf_mm']==kerf for sheet in plan['sheets'] for cut in sheet['internal_cuts']),'Stock tree uses stale kerf.')
            expected_size=(595.2755905511812,841.8897637795277) if revision['spec']['documents']['paper_size']=='a4' else (612,792)
            reader=PdfReader(path/'stock-layout.pdf')
            require(all(abs(float(page.mediabox.width)-expected_size[0])<.01 and abs(float(page.mediabox.height)-expected_size[1])<.01 for page in reader.pages),'Stock PDF uses stale paper size.')
        if 'documents' in manifest['capabilities']:
            original_document_source=json.loads((path/'document-validation.json').read_text())['source_artifact_set_id']
            report['documents']=validate_documents(path,revision['spec'],revision['resolved'],{**metadata,'source_artifact_set_id':original_document_source})
        self.manifests.append((manifest,path))
        write_json(self.output/(kind+'-manifest.json'),manifest)
        return report


def api_process(url,requested_pid,marker):
    parsed=urlparse(url)
    require(parsed.hostname in {'127.0.0.1','localhost','::1'},'Diagnostic requires a loopback API.')
    port=parsed.port or 80
    listeners={item.pid for item in psutil.net_connections(kind='tcp') if item.status==psutil.CONN_LISTEN and item.laddr.port==port and item.pid}
    require(len(listeners)==1,'Unable to identify one local API listener.')
    pid=requested_pid or next(iter(listeners))
    require(pid in listeners,'Provided API PID is not the selected listener.')
    process=psutil.Process(pid)
    require('woodwork.api:create_app' in process.cmdline(),'Selected listener is not the woodworking API.')
    environment=process.environ()
    require(any(environment.get(key)==marker for key in ('OPENAI_API_KEY','ANTHROPIC_API_KEY')),'API was not restarted with the matching synthetic credential marker.')
    require(float(environment.get('WOODWORK_CAD_TIMEOUT','120'))==120 and float(environment.get('WOODWORK_EXPORT_TIMEOUT','120'))==120,'API is not using the required 120 second worker profile.')
    return pid


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--url',default='http://127.0.0.1:8777/api/v1')
    parser.add_argument('--api-pid',type=int)
    parser.add_argument('--prepare',action='store_true',help='Check code/import readiness without contacting the API or generating artifacts.')
    args=parser.parse_args()
    if args.prepare:
        require(args.record.is_file(),'Authored sample record is missing.')
        print(json.dumps({'status':'prepared','native_jobs_started':False}));return
    output=None
    try:
        marker=os.environ.get('WOODWORK_VERIFY_MARKER')
        require(marker is not None and len(marker)>=16,'Set the private synthetic verification marker before the diagnostic.')
        pid=api_process(args.url,args.api_pid,marker)
        appdata=Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'AppData/Local'))).resolve()
        output=args.output.resolve()
        require(output.is_relative_to(appdata) and output!=appdata,'Evidence output must be inside local app data.')
        assert_unlinked(output,appdata);output.mkdir(parents=True,exist_ok=False)
        record=json.loads(args.record.read_text())
        project_id=record['project']['id'];original_id=record['revision']['id']
        with httpx.Client(base_url=args.url,timeout=15) as client:
            client.headers['X-Woodwork-CSRF']=client.get('/session').json()['csrf_token']
            runtime=client.get('/runtime');runtime.raise_for_status();runtime=runtime.json()
            root=Path(runtime['data_root']).resolve()
            cache_namespace(root,Path(__file__).parents[1]/'requirements-runtime.lock',appdata)
            probe=Probe(client,root,output,pid,marker.encode())
            original=probe.snapshot(original_id)
            project=probe.request('GET','/projects/'+project_id)['project']
            base=probe.revision(project['latest_accepted_revision_id'])
            spec=deepcopy(base['spec']);old_kerf=spec['manufacturing']['saw_kerf_mm'];spec['manufacturing']['saw_kerf_mm']='3.2' if old_kerf=='4' else '4'
            assert_only_change(base['spec'],spec,('manufacturing','saw_kerf_mm'))
            kerf=probe.request('POST','/projects/'+project_id+'/revisions',json={'base_revision_id':base['id'],'spec':spec})['revision']
            assert_same_geometry(base['resolved'],kerf['resolved'])
            geometry=probe.job(kerf['id'],'generate')
            stock=probe.job(kerf['id'],'stock',geometry['result_artifact_set_id'])
            kerf_report=probe.verify_revision_set(kerf,'kerf-only')
            spec=deepcopy(kerf['spec']);spec['documents']['paper_size']='letter' if spec['documents']['paper_size']=='a4' else 'a4'
            assert_only_change(kerf['spec'],spec,('documents','paper_size'))
            paper=probe.request('POST','/projects/'+project_id+'/revisions',json={'base_revision_id':kerf['id'],'spec':spec})['revision']
            assert_same_geometry(kerf['resolved'],paper['resolved'])
            geometry=probe.job(paper['id'],'generate')
            documents=probe.job(paper['id'],'documents',geometry['result_artifact_set_id'])
            stock=probe.job(paper['id'],'stock',documents['result_artifact_set_id'])
            paper_report=probe.verify_revision_set(paper,'paper-only')
            require(kerf_report['files']['project.json']!=paper_report['files']['project.json'] and kerf_report['files']['cut-list.csv']!=paper_report['files']['cut-list.csv'],'New option revision did not update source/CSV hashes.')
            require(kerf_report['files']['stock-layout.pdf']!=paper_report['files']['stock-layout.pdf'],'Paper-only stock PDF did not change.')
            require(kerf_report['files']['stock-layout.json']!=paper_report['files']['stock-layout.json'],'New option revision did not update layout source hashes.')
            package=probe.job(paper['id'],'package',stock['result_artifact_set_id'])
            downloaded=client.get('/artifacts/'+package['result_artifact_id']+'/download');downloaded.raise_for_status()
            zip_path=output/'project.zip';zip_path.write_bytes(downloaded.content)
            final_manifest,final_dir=probe.manifest(paper['id'],stock['result_artifact_set_id'])
            package_report=verify_package(zip_path,final_manifest,sha256_file(final_dir/'manifest.json'))
            require(probe.snapshot(original_id)==original,'Original authored revision or artifact bytes changed.')
            require(any(item['kind']=='generate' and item['descendants_sampled']>0 for item in probe.worker_environment_checks),'No running genuine CAD worker and descendant environment was sampled.')
            repository=Path(__file__).parents[1]
            paths=[zip_path]
            for manifest,directory in probe.manifests:
                paths.extend([directory/'manifest.json',*(directory/r['relative_path'] for r in manifest['artifacts'])])
            for job in probe.jobs:
                paths.extend(path for path in (root/'jobs'/job['id']).rglob('*') if path.is_file())
            paths.extend(path for path in (root/'receipts').rglob('*') if path.is_file())
            dist=repository/'apps/web/dist'
            require((dist/'index.html').is_file(),'Production frontend bundle is unavailable for credential scan.')
            paths.extend(path for path in dist.rglob('*') if path.is_file())
            checked=scan_paths(paths,marker.encode())
            require(not any('woodwork.jobs.worker' in child.cmdline() for child in psutil.Process(pid).children(recursive=True)),'An owned worker is active; cache cleanup skipped.')
            before={r['relative_path']:sha256_file(final_dir/r['relative_path']) for r in final_manifest['artifacts']}
            cache_report=recreate_cache(root,repository/'requirements-runtime.lock',appdata)
            reopened=probe.revision(paper['id']);require(reopened['spec']==paper['spec'],'Source project changed after cache recreation.')
            manifest,directory=probe.manifest(paper['id'],stock['result_artifact_set_id']);require(manifest==final_manifest,'Committed manifest changed after cache recreation.')
            for item in manifest['artifacts']:
                response=client.get('/artifacts/'+item['artifact_id']+'/download');response.raise_for_status()
                require(hashlib.sha256(response.content).hexdigest()==before[item['relative_path']],'Committed download changed after cache recreation.')
            require(not any((Path(cache_report['namespace'])).iterdir()),'Reopening committed artifacts depended on rebuilding disposable cache.')
            result={'status':'passed','scope':['J14','A08','B08'],'runtime':'native_windows','data_root':str(root),'api_pid':pid,'cad_timeout_seconds':120,'export_timeout_seconds':120,'base_revision_id':base['id'],'original_revision_id':original_id,'original_sets_unchanged':True,'kerf_only':kerf_report,'paper_only':paper_report,'jobs':probe.jobs,'package':{**package_report,'sha256':sha256_file(zip_path)},'credential_boundary':{'api_marker_confirmed':True,'marker_absent':True,'worker_environment_checks':probe.worker_environment_checks,'files_and_zip_members_scanned':checked,'production_bundle_scanned':True},'cache':{**cache_report,'committed_downloads_verified':len(manifest['artifacts']),'source_reopened':True,'cache_remains_empty':True}}
            write_json(output/'export-options-evidence.json',result)
            print(json.dumps({'status':'passed','evidence':str(output/'export-options-evidence.json')}),flush=True)
    except Exception as error:
        message=str(error) if isinstance(error,DiagnosticError) else 'Diagnostic operation failed: '+type(error).__name__
        if output is not None and output.is_dir():write_json(output/'export-options-failure.json',{'status':'failed','message':message})
        print(json.dumps({'status':'failed','message':message}),flush=True)
        raise SystemExit(1) from None


if __name__=='__main__':main()
