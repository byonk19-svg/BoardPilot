"""Portable inert packages with frozen inventories and separate outer hashes."""
import json
from pathlib import Path
import zipfile
from woodwork.cad_adapter import validate_artifact_set
from woodwork.exports.core import sha256_file


def build_package(source_dir,out_dir,metadata):
    source_dir,out_dir=Path(source_dir).resolve(),Path(out_dir).resolve()
    validate_artifact_set(source_dir,inspect_geometry=False)
    manifest=json.loads((source_dir/'manifest.json').read_text(encoding='utf-8'))
    for key in ('project_id','revision_id','spec_sha256','resolved_sha256'):
        if manifest[key]!=metadata[key]:raise ValueError('Package source differs from frozen revision.')
    if manifest['artifact_set_id']!=metadata['source_artifact_set_id']:raise ValueError('Package source set differs.')
    out_dir.mkdir(parents=True,exist_ok=False)
    path=out_dir/'project.zip'
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for relative in sorted(['manifest.json',*[a['relative_path'] for a in manifest['artifacts']]]):
            info=zipfile.ZipInfo(relative,date_time=(1980,1,1,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16
            archive.writestr(info,(source_dir/relative).read_bytes())
    verify_package(path,manifest,sha256_file(source_dir/'manifest.json'))
    return {'artifact_set_id':manifest['artifact_set_id'],'revision_id':manifest['revision_id'],'manifest_sha256':sha256_file(source_dir/'manifest.json'),'sha256':sha256_file(path),'size_bytes':path.stat().st_size,'relative_path':'project.zip','kind':'zip','mime_type':'application/zip'}


def verify_package(path,expected_manifest,expected_manifest_sha256=None):
    import hashlib
    with zipfile.ZipFile(path) as archive:
        names=archive.namelist()
        required={'manifest.json',*[r['relative_path'] for r in expected_manifest['artifacts']]}
        if len(names)!=len(set(names)) or set(names)!=required:raise ValueError('Package inventory mismatch.')
        manifest_bytes=archive.read('manifest.json')
        if json.loads(manifest_bytes)!=expected_manifest:raise ValueError('Package manifest mismatch.')
        if expected_manifest_sha256 is not None and hashlib.sha256(manifest_bytes).hexdigest()!=expected_manifest_sha256:raise ValueError('Package outer manifest checksum mismatch.')
        for record in expected_manifest['artifacts']:
            data=archive.read(record['relative_path'])
            if len(data)!=record['size_bytes'] or hashlib.sha256(data).hexdigest()!=record['sha256']:
                raise ValueError('Package payload integrity mismatch.')
    return {'status':'passed','artifact_set_id':expected_manifest['artifact_set_id'],'payload_count':len(required)}
