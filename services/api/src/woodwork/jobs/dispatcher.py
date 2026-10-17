"""One local publisher and one atomically contained native worker at a time."""
from dataclasses import asdict
import json
import os
import sqlite3
import re
from pathlib import Path
import sys
import threading

from woodwork.exports.core import sha256_file,write_json
from woodwork.storage import StoreError,new_id,now
from woodwork.storage.paths import contained_file
from woodwork.templates import default_project_spec
from woodwork.application import compile_design
from woodwork.runtime import runtime_versions,classify_runtime_failure
from .environment import worker_environment
from .process import ProcessSupervisor

class DataRootLock:
    def __init__(self,root):
        self.file=(root/'dispatcher.lock').open('a+b')
        if self.file.tell()==0:self.file.write(b'0');self.file.flush()
        self.file.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            self.file.close()
            raise StoreError(503,'DATA_ROOT_BUSY','Another Woodworking Planner process owns this project store.') from None
    def close(self):
        if not self.file.closed:
            self.file.seek(0)
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(self.file.fileno(),fcntl.LOCK_UN)
            self.file.close()

class Dispatcher:
    def __init__(self,store,*,cad_timeout=120,export_timeout=120):
        self.store=store
        self.cad_timeout=cad_timeout
        self.export_timeout=export_timeout
        self.session=new_id('session')
        self.stop=threading.Event()
        self.wake=threading.Event()
        self.supervisor=ProcessSupervisor()
        self.cancel_events={}
        self.thread=None
        self.data_lock=None
        self.last_error=None
    def start(self):
        self.data_lock=DataRootLock(self.store.root)
        self.store.recover_interrupted_jobs()
        with self.store.transaction() as db:
            db.execute("UPDATE proposals SET state='uncertain',diagnostic_code='PROVIDER_INTERRUPTED' WHERE state='pending'")
        self.reconcile()
        self.thread=threading.Thread(target=self.run,daemon=True,name='woodwork-dispatcher')
        self.thread.start()
    def notify(self):self.wake.set()
    def commit_publication(self,job_id,operation,metrics):
        # A verified final directory/receipt already exists. A database failure
        # remains recoverable rather than turning into a terminal native failure.
        try:operation()
        except sqlite3.Error:
            self.last_error='PUBLICATION_PENDING'
            cancelled=self.store.get_job(job_id)['state'] in {'cancelled','cancelling'}
            self.store.finish_job(job_id,'cancelled' if cancelled else 'interrupted','CANCELLED' if cancelled else 'PUBLICATION_PENDING',metrics)
        except StoreError as error:
            if error.code=='JOB_NOT_PUBLISHABLE' and self.store.get_job(job_id)['state'] in {'cancelled','cancelling'}:
                self.store.finish_job(job_id,'cancelled','CANCELLED',metrics)
            else:raise
    def verify_result_identity(self,manifest,metadata,resolved):
        expected={**metadata,'spec_sha256':resolved['spec_sha256'],'resolved_sha256':resolved['resolved_sha256']}
        for key in ('project_id','revision_id','revision_number','artifact_set_id','source_artifact_set_id','spec_sha256','resolved_sha256'):
            if manifest.get(key)!=expected[key]:raise StoreError(409,'RESULT_BINDING_MISMATCH','The worker result differs from its immutable job snapshot.')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,99}',manifest['artifact_set_id']):raise StoreError(409,'RESULT_BINDING_MISMATCH','The worker result identifier is invalid.')
    def cancel(self,job_id):
        result=self.store.cancel_job(job_id)
        event=self.cancel_events.get(job_id)
        if event:event.set()
        self.wake.set()
        return result
    def close(self):
        self.stop.set();self.wake.set()
        self.supervisor.close()
        if self.thread:self.thread.join(timeout=6)
        if self.thread and self.thread.is_alive():raise RuntimeError('Dispatcher did not stop after owned workers exited')
        if self.data_lock:self.data_lock.close()
    def reconcile(self):
        receipts=self.store.root/'receipts'
        receipts.mkdir(exist_ok=True)
        for path in receipts.glob('*.json'):
            try:
                receipt=json.loads(path.read_text(encoding='utf-8'))
                job=self.store.get_job(receipt['job_id'])
                if job['state'] in {'succeeded','cancelled','failed','cancelling'}:continue
                directory=self.store.root/receipt['relative_dir']
                if receipt.get('kind')=='package':
                    record=receipt['record']
                    package=contained_file(self.store.root,receipt['relative_dir']+'/'+record['relative_path'])
                    if package.stat().st_size!=record['size_bytes'] or sha256_file(package)!=record['sha256']:continue
                    source=self.store.get_artifact_set(job['source_artifact_set_id'])
                    from woodwork.exports.package import verify_package
                    verify_package(package,source['manifest'],source['manifest_sha256'])
                    self.store.publish_package(job['id'],record,receipt['relative_dir'])
                    continue
                from woodwork.cad_adapter import validate_artifact_set
                manifest_path=contained_file(self.store.root,receipt['relative_dir']+'/manifest.json')
                validate_artifact_set(manifest_path.parent,inspect_geometry=False)
                if sha256_file(manifest_path)!=receipt['manifest_sha256']:continue
                manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
                self.store.publish_result(job['id'],manifest,receipt['relative_dir'],receipt['manifest_sha256'])
            except (ValueError,OSError,KeyError,StoreError):
                self.last_error='ORPHAN_RECONCILIATION_REQUIRED'
    def run(self):
        while not self.stop.is_set():
            job=self.store.claim_job(self.session)
            if job is None:
                self.wake.wait(.5);self.wake.clear();continue
            try:self.execute(job)
            except Exception:
                self.last_error='DISPATCHER_OPERATION_FAILED'
                cancelled=self.store.get_job(job['id'])['state'] in {'cancelled','cancelling'}
                self.store.finish_job(job['id'],'cancelled' if cancelled else ('interrupted' if self.stop.is_set() else 'failed'),'CANCELLED' if cancelled else self.last_error)
    def execute(self,job):
        job_root=self.store.root/'jobs'/job['id']
        job_root.mkdir(parents=True)
        cancellation=threading.Event()
        self.cancel_events[job['id']]=cancellation
        try:
            if self.store.get_job(job['id'])['state']=='cancelling':
                self.store.finish_job(job['id'],'cancelled','CANCELLED');return
            if job['kind']=='preflight':
                spec=default_project_spec();resolved=compile_design(spec)
                metadata={'project_id':'runtime_preflight','revision_id':new_id('preflight'),'revision_number':1,'artifact_set_id':new_id('set'),'source_artifact_set_id':None}
            else:
                revision=self.store.get_revision(job['revision_id'])
                spec,resolved=revision['spec'],revision['resolved']
                metadata={'project_id':revision['project_id'],'revision_id':revision['id'],'revision_number':revision['number'],'artifact_set_id':new_id('set'),'source_artifact_set_id':job['source_artifact_set_id'],'spec_sha256':revision['spec_sha256'],'resolved_sha256':revision['resolved_sha256']}
            payload={'kind':job['kind'],'spec':spec,'resolved':resolved,'metadata':metadata}
            if job['source_artifact_set_id']:
                source=self.store.get_artifact_set(job['source_artifact_set_id'])
                payload['source_relative_dir']=source['relative_dir']
            write_json(job_root/'input.json',payload)
            environment=worker_environment(self.store.root)
            def on_event(event):
                if isinstance(event,dict) and 'stage' in event:self.store.update_stage(job['id'],event['stage'])
            timeout=self.cad_timeout if job['kind'] in {'generate','preflight'} else self.export_timeout
            result=self.supervisor.run([sys.executable,'-u','-m','woodwork.jobs.worker',str(job_root)],cwd=Path(__file__).resolve().parents[5],env=environment,log_path=job_root/'worker.log',timeout_seconds=timeout,cancel_event=cancellation,on_event=on_event)
            metrics={'elapsed_seconds':result.elapsed_seconds,'peak_sampled_process_tree_rss_bytes':result.peak_rss_bytes}
            if cancellation.is_set() or self.store.get_job(job['id'])['state'] in {'cancelling','cancelled'}:self.store.finish_job(job['id'],'cancelled','CANCELLED',metrics);return
            if self.stop.is_set():self.store.finish_job(job['id'],'interrupted','COORDINATOR_INTERRUPTED',metrics);return
            if result.cancelled:self.store.finish_job(job['id'],'cancelled','CANCELLED',metrics);return
            if result.timed_out:
                self.store.finish_job(job['id'],'failed','CAD_TIMEOUT' if job['kind']=='generate' else 'WORKER_TIMEOUT',metrics)
                if job['kind']=='preflight':
                    write_json(self.store.root/'runtime-preflight.json',{'status':'failed','checked_at':now(),**runtime_versions(),'kernel_probe':'failed','metrics':metrics,'diagnostic':{'code':'WORKER_TIMEOUT','message':'The CAD preflight exceeded its local time limit.','guidance':'Run preflight again and inspect its job diagnostics if the timeout repeats.'}})
                return
            if result.returncode:
                code='WORKER_FAILED'
                for line in result.log_tail.splitlines():
                    try:
                        event=json.loads(line)
                        if isinstance(event,dict) and 'error_code' in event:code=event['error_code']
                    except ValueError:pass
                self.store.finish_job(job['id'],'failed',code,metrics)
                if job['kind']=='preflight':
                    private=(job_root/'worker-error.txt').read_text(encoding='utf-8') if (job_root/'worker-error.txt').is_file() else ''
                    write_json(self.store.root/'runtime-preflight.json',{'status':'failed','checked_at':now(),**runtime_versions(),'diagnostic':classify_runtime_failure(private)})
                return
            if job['kind']=='package':
                record=json.loads((job_root/'result.json').read_text(encoding='utf-8'))
                record['artifact_id']=new_id('artifact')
                source=self.store.get_artifact_set(job['source_artifact_set_id'])
                from woodwork.exports.package import verify_package
                verify_package(job_root/'out/project.zip',source['manifest'],source['manifest_sha256'])
                expected={'artifact_set_id':source['id'],'revision_id':source['revision_id'],'manifest_sha256':source['manifest_sha256'],'sha256':sha256_file(job_root/'out/project.zip'),'size_bytes':(job_root/'out/project.zip').stat().st_size,'relative_path':'project.zip','kind':'zip','mime_type':'application/zip'}
                if any(record.get(k)!=v for k,v in expected.items()):raise ValueError('Package result differs from independently verified frozen bytes.')
                final=self.store.root/'exports'/record['artifact_id']
                final.parent.mkdir(exist_ok=True)
                relative=final.relative_to(self.store.root).as_posix()
                receipt={'kind':'package','job_id':job['id'],'relative_dir':relative,'record':record}
                write_json(self.store.root/'receipts'/f"{record['artifact_id']}.json",receipt)
                (job_root/'out').rename(final)
                self.commit_publication(job['id'],lambda:self.store.publish_package(job['id'],record,relative,metrics),metrics)
                return
            from woodwork.cad_adapter import validate_artifact_set
            validate_artifact_set(job_root/'out',inspect_geometry=False)
            manifest=json.loads((job_root/'out/manifest.json').read_text(encoding='utf-8'))
            self.verify_result_identity(manifest,metadata,resolved)
            if job['kind']=='preflight':
                write_json(self.store.root/'runtime-preflight.json',{'status':'passed','checked_at':now(),**runtime_versions(),'kernel_probe':'passed','metrics':metrics})
                self.store.finish_job(job['id'],'succeeded',metrics=metrics);return
            self.store.update_stage(job['id'],'publishing')
            final=self.store.root/'artifacts'/manifest['artifact_set_id']
            final.parent.mkdir(exist_ok=True)
            if final.exists():raise StoreError(409,'ARTIFACT_SET_EXISTS','An immutable artifact set cannot be replaced.')
            relative=final.relative_to(self.store.root).as_posix()
            receipt={'job_id':job['id'],'relative_dir':relative,'manifest_sha256':sha256_file(job_root/'out/manifest.json')}
            write_json(self.store.root/'receipts'/f"{manifest['artifact_set_id']}.json",receipt)
            (job_root/'out').rename(final)
            self.commit_publication(job['id'],lambda:self.store.publish_result(job['id'],manifest,relative,receipt['manifest_sha256'],metrics),metrics)
            if job['kind']=='generate':
                write_json(self.store.root/'runtime-preflight.json',{'status':'passed','checked_at':now(),**runtime_versions(),'kernel_probe':'passed','metrics':metrics})
        finally:self.cancel_events.pop(job['id'],None)
