"""Real loopback API/native worker fault demonstration in a new disposable store."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid
import httpx
import psutil
from woodwork.cad_adapter import validate_artifact_set
from woodwork.domain import canonical_json
from woodwork.exports.core import sha256_file,write_json
from woodwork.storage import Store,now


def seed(root,source):
    validate_artifact_set(source,inspect_geometry=False)
    manifest=json.loads((source/'manifest.json').read_text())
    spec=json.loads((source/'project.json').read_text())
    resolved=json.loads((source/'resolved-project.json').read_text())
    store=Store(root)
    with store.transaction() as db:
        stamp=now()
        db.execute('INSERT INTO projects(id,title,created_at,updated_at,latest_accepted_revision_id) VALUES(?,?,?,?,?)',(manifest['project_id'],'Recovery diagnostic',stamp,stamp,manifest['revision_id']))
        db.execute('INSERT INTO revisions(id,project_id,number,spec_json,resolved_json,spec_sha256,resolved_sha256,created_at) VALUES(?,?,?,?,?,?,?,?)',(manifest['revision_id'],manifest['project_id'],manifest['revision_number'],canonical_json(spec),canonical_json(resolved),manifest['spec_sha256'],manifest['resolved_sha256'],stamp))
    target=root/'artifacts'/manifest['artifact_set_id']
    shutil.copytree(source,target)
    job=store.queue_job(manifest['revision_id'],'generate','verified-seed')
    store.claim_job('seed-existing-genuine-set')
    store.publish_result(job['id'],manifest,target.relative_to(root).as_posix(),sha256_file(target/'manifest.json'))
    return store,manifest


def wait_until(predicate,seconds=12):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        value=predicate()
        if value:return value
        time.sleep(.1)
    raise TimeoutError('Diagnostic condition did not occur before its deadline.')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--port',type=int,default=8788)
    args=parser.parse_args()
    root=args.output.resolve();root.mkdir(parents=True,exist_ok=False)
    store,manifest=seed(root,args.source.resolve())
    repository=Path(__file__).resolve().parents[1]
    api=None;log=None
    client=httpx.Client(base_url=f'http://127.0.0.1:{args.port}/api/v1',timeout=10)
    observations=[]
    def start():
        nonlocal api,log
        log=(root/('api-'+uuid.uuid4().hex+'.log')).open('wb')
        env=os.environ.copy();env['WOODWORK_DATA_ROOT']=str(root)
        api=subprocess.Popen([sys.executable,'-m','uvicorn','woodwork.api:create_app','--factory','--host','127.0.0.1','--port',str(args.port)],cwd=repository,env=env,stdout=log,stderr=subprocess.STDOUT)
        def ready():
            try:return client.get('/health').status_code==200
            except httpx.RequestError:return False
        wait_until(ready,20)
        client.headers['X-Woodwork-CSRF']=client.get('/session').json()['csrf_token']
    def submit(key):
        response=client.post(f"/revisions/{manifest['revision_id']}/jobs",json={'kind':'generate','idempotency_key':key})
        response.raise_for_status();return response.json()['job']['id']
    def native_worker():
        for process in psutil.Process(api.pid).children(recursive=True):
            try:
                if 'woodwork.jobs.worker' in process.cmdline():return process
            except (psutil.NoSuchProcess,psutil.AccessDenied):pass
        return None
    def job(identifier):return client.get('/jobs/'+identifier).json()['job']
    def complete(identifier):
        result=wait_until(lambda:job(identifier) if job(identifier)['state'] in {'succeeded','failed','cancelled','interrupted'} else None,130)
        assert result['state']=='succeeded',result
        response=client.get(f"/revisions/{manifest['revision_id']}/manifest")
        response.raise_for_status()
        validate_artifact_set(root/'artifacts'/response.json()['artifact_set_id'])
        return result
    try:
        start()
        crash=submit('actual-native-crash')
        worker=wait_until(native_worker,15)
        wait_until(lambda:job(crash)['stage'] in {'generating_geometry','generating_side_panels','generating_horizontal_panels','generating_back_panel','assembling_geometry'},15)
        owned=worker.children(recursive=True)
        worker.kill()
        failed=wait_until(lambda:job(crash) if job(crash)['state']=='failed' else None,10)
        wait_until(lambda:all(not p.is_running() for p in owned),5)
        assert client.get('/health').status_code==200
        assert store.get_revision(manifest['revision_id'])['preferred_artifact_set_id']==manifest['artifact_set_id']
        observations.append({'case':'native_worker_crash','failed_job':failed,'api_available':True,'prior_set_preserved':True,'owned_descendants_exited':True})
        after_crash=complete(submit('valid-after-crash'))
        observations.append({'case':'valid_after_native_crash','job':after_crash})
        prior=store.get_revision(manifest['revision_id'])['preferred_artifact_set_id']
        interrupted=submit('actual-coordinator-interruption')
        worker=wait_until(native_worker,15)
        wait_until(lambda:job(interrupted)['stage'] in {'generating_geometry','generating_side_panels','generating_horizontal_panels','generating_back_panel','assembling_geometry'},15)
        owned=[worker,*worker.children(recursive=True)]
        api.kill();api.wait(timeout=10);log.close();api=None
        wait_until(lambda:all(not p.is_running() for p in owned),5)
        start()
        result=job(interrupted)
        assert result['state']=='interrupted',result
        assert store.get_revision(manifest['revision_id'])['preferred_artifact_set_id']==prior
        observations.append({'case':'coordinator_restart','job':result,'prior_set_preserved':True,'owned_processes_exited':True})
        recovered=complete(submit('valid-after-interruption'))
        observations.append({'case':'valid_after_restart','job':recovered})
        write_json(root/'recovery-evidence.json',{'status':'passed','source_artifact_set_id':manifest['artifact_set_id'],'runtime':'native_windows','observations':observations})
        print(json.dumps({'status':'passed','evidence':str(root/'recovery-evidence.json')}),flush=True)
    finally:
        client.close()
        if api is not None:
            api.terminate()
            try:api.wait(timeout=10)
            except subprocess.TimeoutExpired:api.kill();api.wait(timeout=5)
        if log is not None and not log.closed:log.close()


if __name__=='__main__':main()
