"""Fixed application worker entry point. Immutable JSON is data, never code."""
import json
from pathlib import Path
import sys
import re
from woodwork.cad_adapter.windows_runtime import configure_native_platform

configure_native_platform()

CURRENT_STAGE='validating'

class WorkerError(ValueError):
    def __init__(self,code,message):
        self.code=code
        super().__init__(message)


def event(stage):
    global CURRENT_STAGE
    CURRENT_STAGE=stage
    print(json.dumps({'stage':stage}),flush=True)

def validate_metadata(metadata,kind):
    allowed={'project_id','revision_id','revision_number','artifact_set_id','source_artifact_set_id','spec_sha256','resolved_sha256'}
    required={'project_id','revision_id','revision_number'}
    if not isinstance(metadata,dict) or not required<=set(metadata) or not set(metadata)<=allowed or type(metadata['revision_number']) is not int or metadata['revision_number']<1:
        raise WorkerError('JOB_CONTRACT_INVALID','Revision metadata does not match the trusted contract.')
    for key in ('project_id','revision_id','artifact_set_id','source_artifact_set_id'):
        if key in metadata and metadata[key] is not None and (not isinstance(metadata[key],str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,99}',metadata[key])):
            raise WorkerError('JOB_CONTRACT_INVALID','Revision identifiers are invalid.')
    for key in ('spec_sha256','resolved_sha256'):
        if key in metadata and (not isinstance(metadata[key],str) or not re.fullmatch(r'[0-9a-f]{64}',metadata[key])):
            raise WorkerError('JOB_CONTRACT_INVALID','Revision checksums are invalid.')
    if kind=='generate' and metadata.get('source_artifact_set_id') is not None:
        raise WorkerError('JOB_CONTRACT_INVALID','Generation cannot select a prior artifact set.')


def main(job_root):
    from woodwork.domain import hash_json
    from woodwork.application import compile_design as compile_project
    from woodwork.cad_adapter import build_artifact_set, validate_artifact_set
    event('validating')
    with (job_root/'input.json').open('rb') as stream:
        data=stream.read(512*1024+1)
    if len(data)>512*1024:
        raise ValueError('Job input exceeds limit')
    job=json.loads(data)
    if not isinstance(job,dict) or job.get('kind') not in {'generate','preflight','documents','stock','package'}:
        raise WorkerError('JOB_CONTRACT_INVALID','Unsupported trusted job contract')
    fields={'kind','spec','resolved','metadata'}
    if job['kind'] in {'documents','stock','package'}:fields.add('source_relative_dir')
    if set(job)!=fields:raise WorkerError('JOB_CONTRACT_INVALID','Unexpected trusted job fields')
    validate_metadata(job['metadata'],job['kind'])
    event('compiling')
    trusted=compile_project(job['spec'])
    if hash_json(trusted)!=hash_json(job['resolved']):
        raise WorkerError('SOURCE_MISMATCH','Immutable ledger source mismatch')
    if job['kind'] in {'generate','preflight'}:
        manifest=build_artifact_set(job['spec'],trusted,job['metadata'],job_root/'out',progress=event,owned_process=True)
        # The adapter already reopens and measures the exact STEP/GLB bytes and
        # binds their hashes into its inspection report. Verify that inventory
        # again before publication without repeating the same native booleans.
        event('verifying_artifacts')
        validate_artifact_set(job_root/'out',inspect_geometry=False)
    else:
        from woodwork.storage.paths import contained_file
        root=job_root.parents[1]
        source_manifest=contained_file(root,job['source_relative_dir']+'/manifest.json')
        source=source_manifest.parent
        source_info=json.loads(source_manifest.read_text(encoding='utf-8'))
        for key in ('project_id','revision_id','spec_sha256','resolved_sha256'):
            if source_info[key]!=job['metadata'][key]:raise WorkerError('SOURCE_MISMATCH','Derived job source differs from the immutable revision.')
        if source_info['artifact_set_id']!=job['metadata']['source_artifact_set_id']:
            raise WorkerError('SOURCE_MISMATCH','Derived job source set identity differs.')
        validate_artifact_set(source,inspect_geometry=False)
        if job['kind']=='documents':
            from woodwork.exports.documents import add_documents,validate_documents
            event('generating_documents')
            manifest=add_documents(source,job_root/'out',job['metadata'],job['spec'],trusted,progress=event)
            validate_documents(job_root/'out',job['spec'],trusted,job['metadata'])
        elif job['kind']=='stock':
            from woodwork.exports.stock import add_stock
            event('planning_stock')
            manifest=add_stock(source,job_root/'out',job['metadata'],job['spec'],trusted)
        else:
            from woodwork.exports.package import build_package
            event('packaging')
            result=build_package(source,job_root/'out',job['metadata'])
            (job_root/'result.json').write_text(json.dumps(result),encoding='utf-8')
            return
    (job_root/'result.json').write_text(json.dumps({'artifact_set_id':manifest['artifact_set_id'],'revision_id':manifest['revision_id']}),encoding='utf-8')


if __name__=='__main__':
    try:
        if len(sys.argv)!=2:
            raise ValueError('Worker needs an application-owned job directory')
        main(Path(sys.argv[1]).resolve())
    except Exception as error:
        import traceback
        if len(sys.argv)==2:
            try:
                (Path(sys.argv[1])/'worker-error.txt').write_text(traceback.format_exc()[-65536:],encoding='utf-8')
            except OSError:
                pass
        from woodwork.domain import DomainError
        from woodwork.cad_adapter import CadValidationError
        if isinstance(error,WorkerError):code=error.code
        elif isinstance(error,DomainError):code='PARAMETER_INVALID'
        elif isinstance(error,CadValidationError):code='CAD_INSPECTION_FAILED' if CURRENT_STAGE in {'inspecting_geometry','verifying_artifacts'} else 'CAD_GENERATION_FAILED'
        else:code='WORKER_FAILED'
        print(json.dumps({'error_code':code,'stage':CURRENT_STAGE,'message':'Trusted operation failed; no artifact set was published.'}),flush=True)
        raise SystemExit(1)
