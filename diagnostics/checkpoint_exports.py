"""Actual local jobs verify selected PDF units/precision and frozen ZIP bytes."""
import argparse
import json
import os
from pathlib import Path
import time
import uuid

import httpx
from pypdf import PdfReader
from woodwork.cad_adapter.windows_runtime import configure_native_platform
from woodwork.jobs.environment import worker_environment
from woodwork.exports.core import write_json
from woodwork.exports.package import verify_package


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--api',required=True)
    parser.add_argument('--data-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--project-id',help='Resume this diagnostic\'s unchanged metric checkpoint project.')
    args=parser.parse_args()
    environment=worker_environment(args.data_root)
    for key in ('CADGEN_DAEMON','CADGEN_JOBS','CADGEN_TELEMETRY','CADGEN_UPDATE_CHECK',
                'CADGEN_CACHE_DIR','CADGEN_STATE_DIR','MPLCONFIGDIR'):
        os.environ[key]=environment[key]
    configure_native_platform()
    from woodwork.cad_adapter import validate_artifact_set
    client=httpx.Client(base_url=args.api,timeout=15)
    client.headers['X-Woodwork-CSRF']=client.get('/session').json()['csrf_token']
    job_evidence=args.output.with_name('export-jobs.json')
    observed_jobs=json.loads(job_evidence.read_text()) if job_evidence.is_file() else []
    def post(path,body):
        response=client.post(path,json=body);response.raise_for_status();return response.json()
    def wait(job):
        deadline=time.monotonic()+130
        while time.monotonic()<deadline:
            response=client.get('/jobs/'+job['id']);response.raise_for_status();current=response.json()['job']
            if current['state'] in {'succeeded','failed','cancelled','interrupted'}:
                observed_jobs.append(current)
                args.output.parent.mkdir(parents=True,exist_ok=True)
                write_json(job_evidence,observed_jobs)
                assert current['state']=='succeeded',current
                return current
            time.sleep(.25)
        raise TimeoutError(job['id'])
    def queue(revision,kind,source=None):
        body={'kind':kind,'idempotency_key':'checkpoint-'+uuid.uuid4().hex}
        if source:body['source_artifact_set_id']=source
        return wait(post('/revisions/'+revision+'/jobs',body)['job'])
    spec=client.get('/templates').json()['templates'][0]['default_spec']
    spec['project_name']='Checkpoint units in (garage)'
    spec['display']['fraction_denominator']=16
    spec['documents']['schedule_units']='mm'
    if args.project_id:
        response=client.get('/projects/'+args.project_id);response.raise_for_status();created=response.json()
        response=client.get('/revisions/'+created['project']['latest_accepted_revision_id']);response.raise_for_status()
        created['revision']=response.json()['revision']
        assert created['project']['title']==spec['project_name'] and created['revision']['spec']==spec
    else:
        created=post('/projects',{'title':spec['project_name'],'spec':spec})
    revision=created['revision'];cases=[]
    for units in ('mm','dual'):
        if units=='dual':
            spec['documents']['schedule_units']='dual'
            revision=post('/projects/'+created['project']['id']+'/revisions',{'base_revision_id':revision['id'],'spec':spec})['revision']
        response=client.get('/revisions/'+revision['id']);response.raise_for_status()
        generated=next((job for job in response.json()['jobs'] if job['kind']=='generate' and job['state']=='succeeded'),None)
        fresh_generation=generated is None
        if generated is None:generated=queue(revision['id'],'generate')
        # Runtime evidence is written after artifact/job publication. It is
        # optional metadata, not part of that database transaction.
        probe_path=args.data_root/'runtime-preflight.json'
        deadline=time.monotonic()+5
        while time.monotonic()<deadline:
            try:probe=probe_path.read_bytes()
            except FileNotFoundError:time.sleep(.1);continue
            if not fresh_generation or json.loads(probe).get('metrics')==generated['metrics']:break
            time.sleep(.1)
        else:raise TimeoutError('Generation runtime evidence did not finish publishing.')
        documents=queue(revision['id'],'documents',generated['result_artifact_set_id'])
        stock=queue(revision['id'],'stock',documents['result_artifact_set_id'])
        root=args.data_root/'artifacts'/stock['result_artifact_set_id']
        checked=validate_artifact_set(root,inspect_geometry=True)
        manifest=json.loads((root/'manifest.json').read_text())
        assert checked['revision_id']==revision['id']
        text=' '.join(' '.join(page.extract_text() for page in PdfReader(root/'design-packet.pdf').pages).split())
        assert 'Checkpoint units in (garage)' in text
        if units=='mm':
            assert 'Local width W 298.8 mm' in text and 'Unit reference 25.4 mm' in text
        else:
            assert 'approx. 11 3/4 in (298.8 mm)' in text
            assert '11 49/64 in (298.8 mm)' not in text
        evidence=json.loads((root/'document-validation.json').read_text())
        assert evidence['application_units']==units and evidence['native_units']=='mm'
        for part in manifest['part_definitions']:
            pdf=PdfReader(root/f"drawings/{part['definition_id']}-metric.pdf")
            assert pdf.metadata['/WoodworkUnits']=='mm'
        stock_evidence=json.loads((root/'stock-validation.json').read_text())
        assert stock_evidence['application_units']==units and stock_evidence['cut_tree_replay']=='passed'
        package=wait(post('/revisions/'+revision['id']+'/package',{'artifact_set_id':manifest['artifact_set_id'],'idempotency_key':'checkpoint-'+uuid.uuid4().hex})['job'])
        response=client.get('/artifacts/'+package['result_artifact_id']+'/download');response.raise_for_status()
        args.output.parent.mkdir(parents=True,exist_ok=True)
        archive=args.output.parent/('checkpoint-'+units+'.zip');archive.write_bytes(response.content)
        zipped=verify_package(archive,manifest)
        assert (args.data_root/'runtime-preflight.json').read_bytes()==probe
        row={'units':units,'fraction_denominator':16,'revision_id':revision['id'],'artifact_set_id':manifest['artifact_set_id'],'artifact_directory':str(root),
             'native_geometry':checked['status'],'cad_probe_preserved_after_exports':True,
             'jobs':{'generate':generated,'documents':documents,'stock':stock,'package':package},'zip':zipped,
             'pdfs':[a for a in manifest['artifacts'] if a['kind']=='pdf']}
        cases.append(row);write_json(args.output,{'status':'in_progress','cases':cases})
        print(json.dumps({'units':units,'status':'passed','revision_id':revision['id'],'zip_payloads':zipped['payload_count']}),flush=True)
    write_json(args.output,{'status':'passed','cases':cases,'visual_review':'required_separately'})


if __name__=='__main__':main()
