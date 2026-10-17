"""Create/extend one genuine demonstration project through the running API."""
import argparse
import json
from pathlib import Path
import time
import uuid
import httpx
from woodwork.templates import default_project_spec
from woodwork.recipes import RECIPE_ID,RECIPE_VERSION
from woodwork.exports.core import write_json


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('stage',choices=['geometry','documents','stock','package'])
    parser.add_argument('--record',type=Path,required=True)
    parser.add_argument('--url',default='http://127.0.0.1:8777/api/v1')
    args=parser.parse_args()
    client=httpx.Client(base_url=args.url,timeout=10)
    client.headers['X-Woodwork-CSRF']=client.get('/session').json()['csrf_token']
    if args.stage=='geometry':
        if args.record.exists():
            record=json.loads(args.record.read_text())
        else:
            record=None
        spec=default_project_spec()
        spec['dimensions']['outside_depth_mm']='355.6'
        spec['materials']['main']['actual_thickness_mm']='19.05'
        spec['materials']['back']['actual_thickness_mm']='6.35'
        spec['construction']['recipe']={'id':RECIPE_ID,'version':RECIPE_VERSION}
        spec['documents']['paper_size']='a4'
        if record is None:
            response=client.post('/projects',json={'title':'Authored recipe example (actual 19.05 mm)','spec':spec})
            response.raise_for_status();record=response.json()
        args.record.parent.mkdir(parents=True,exist_ok=True)
    else:record=json.loads(args.record.read_text())
    revision=record['revision']['id']
    payload={'idempotency_key':'demo-'+args.stage+'-'+uuid.uuid4().hex}
    endpoint=f'/revisions/{revision}/jobs'
    if args.stage=='package':endpoint=f'/revisions/{revision}/package'
    else:
        payload['kind']='generate' if args.stage=='geometry' else args.stage
        if args.stage!='geometry':payload['source_artifact_set_id']=client.get(f'/revisions/{revision}/manifest').json()['artifact_set_id']
    response=client.post(endpoint,json=payload);response.raise_for_status();job=response.json()['job']
    record.setdefault('jobs',{})[args.stage]=job
    write_json(args.record,record)
    last=None;deadline=time.monotonic()+135
    while time.monotonic()<deadline:
        current=client.get('/jobs/'+job['id']).json()['job']
        if current['stage']!=last:print(json.dumps({'stage':current['stage'],'state':current['state']}),flush=True);last=current['stage']
        if current['state'] in {'succeeded','failed','cancelled','interrupted'}:
            record['jobs'][args.stage]=current
            write_json(args.record,record)
            if current['state']!='succeeded':raise RuntimeError(current)
            print(json.dumps({'status':'passed','job':current,'record':str(args.record.resolve())}),flush=True)
            return
        time.sleep(1)
    raise TimeoutError('Sample job did not complete.')


if __name__=='__main__':main()
