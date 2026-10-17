"""Copy a verified immutable set and rebind its new artifact identities."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import uuid
from woodwork.cad_adapter import validate_artifact_set
from woodwork.cad_adapter.verifier import require
from woodwork.exports.core import artifact_record,write_json


def copy_verified_set(source_dir,out_dir,metadata):
    source_dir,out_dir=Path(source_dir).resolve(),Path(out_dir).resolve()
    validate_artifact_set(source_dir,inspect_geometry=False)
    source=json.loads((source_dir/'manifest.json').read_text())
    require(not out_dir.exists(),'Cumulative output directory must be new.')
    for key in ('project_id','revision_id','revision_number','spec_sha256','resolved_sha256'):
        require(metadata[key]==source[key],'Cumulative source differs from immutable revision.')
    require(metadata['source_artifact_set_id']==source['artifact_set_id'],'Cumulative source set differs.')
    out_dir.mkdir(parents=True)
    for record in source['artifacts']:
        target=out_dir/record['relative_path'];target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source_dir/record['relative_path'],target)
    records={r['relative_path']:artifact_record(out_dir,r['relative_path'],r['kind'],r['mime_type'],metadata,r['definition_id']) for r in source['artifacts']}
    sidecar=json.loads((out_dir/'step-instance-map.json').read_text())
    sidecar['assembly_artifact_id']=records['assembly.step']['artifact_id']
    write_json(out_dir/'step-instance-map.json',sidecar)
    records['step-instance-map.json']=artifact_record(out_dir,'step-instance-map.json','json','application/json',metadata)
    manifest=deepcopy(source)
    manifest.update(artifact_set_id=metadata.get('artifact_set_id',str(uuid.uuid4())),source_artifact_set_id=source['artifact_set_id'],artifacts=list(records.values()))
    return manifest,records
