"""Verify a new cumulative PDF/stock/ZIP set from the dimension-edit test store."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import uuid

import httpx
from pypdf import PdfReader
from woodwork.cad_adapter.windows_runtime import configure_native_platform
configure_native_platform()
from woodwork.cad_adapter import validate_artifact_set
from woodwork.exports.core import write_json
from woodwork.exports.package import verify_package


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--api',required=True)
    parser.add_argument('--data-root',type=Path,required=True)
    parser.add_argument('--cases',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    cases=json.loads(args.cases.read_text(encoding='utf-8'))
    assert [c['revision'] for c in cases]==[1,2,3,4,4]
    case=cases[-1]; revision=case['revision_id']
    client=httpx.Client(base_url=args.api,timeout=15)
    client.headers['X-Woodwork-CSRF']=client.get('/session').json()['csrf_token']
    def wait(job):
        deadline=time.monotonic()+125
        while time.monotonic()<deadline:
            response=client.get('/jobs/'+job['id']); response.raise_for_status(); current=response.json()['job']
            if current['state'] in {'succeeded','failed','cancelled','interrupted'}:
                assert current['state']=='succeeded',current
                return current
            time.sleep(.25)
        raise TimeoutError(job['id'])
    existing=client.get('/revisions/'+revision).json()['jobs']
    documents=next((j for j in existing if j['kind']=='documents' and j['state']=='succeeded' and j['source_artifact_set_id']==case['artifact_set_id'] and j['idempotency_key'].startswith('export-check-')),None)
    if documents is None:
        response=client.post('/revisions/'+revision+'/jobs',json={'kind':'documents','idempotency_key':'export-check-'+uuid.uuid4().hex,'source_artifact_set_id':case['artifact_set_id']})
        response.raise_for_status(); documents=wait(response.json()['job'])
    root=args.data_root/'artifacts'/documents['result_artifact_set_id']
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    checked=validate_artifact_set(root,inspect_geometry=True)
    assert manifest['revision_id']==revision and set(manifest['capabilities'])=={'geometry','documents','stock_layout','cost_estimate'}
    assert manifest['validation']=={'parameters':'passed','geometry':'passed','documents':'passed','stock_layout':'passed'}
    pdfs=[{'relative_path':a['relative_path'],'pages':len(PdfReader(root/a['relative_path']).pages),'sha256':a['sha256']} for a in manifest['artifacts'] if a['kind']=='pdf']
    response=client.post('/revisions/'+revision+'/package',json={'artifact_set_id':manifest['artifact_set_id'],'idempotency_key':'package-check-'+uuid.uuid4().hex})
    response.raise_for_status(); package=wait(response.json()['job'])
    response=client.get('/artifacts/'+package['result_artifact_id']+'/download');response.raise_for_status()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    path=args.output.with_suffix('.zip');path.write_bytes(response.content)
    packaged=verify_package(path,manifest)
    result={'status':'passed','revision_id':revision,'artifact_set_id':manifest['artifact_set_id'],'native_geometry':checked['status'],'capabilities':manifest['capabilities'],'document_job':documents,'package_job':package,'pdfs':pdfs,'package':packaged,'zip_sha256':hashlib.sha256(response.content).hexdigest(),'pdf_visual_review':'separate rendered review required'}
    write_json(args.output,result)
    print(json.dumps({'status':'passed','set':str(root),'pdf_pages':sum(p['pages'] for p in pdfs),'package_payloads':packaged['payload_count']}),flush=True)


if __name__=='__main__':main()
