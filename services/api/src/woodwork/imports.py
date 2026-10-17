"""Bounded ZIP inspection; uploaded geometry never becomes trusted local output."""
import io
import json
from pathlib import Path,PurePosixPath
import re
import shutil
import stat
import zipfile
from woodwork.application import compile_design
from woodwork.cad_adapter import validate_artifact_set
from woodwork.domain import hash_json,DomainError
from woodwork.exports.core import sha256_file,write_json
from woodwork.storage import StoreError,new_id

COMPRESSED_LIMIT=32*1024*1024
EXPANDED_LIMIT=128*1024*1024
FILE_LIMIT=48*1024*1024
ENTRY_LIMIT=120
EXTENSIONS={'json':'.json','csv':'.csv','text':'.txt','pdf':'.pdf','step':'.step','glb':'.glb'}


class ImportSizeError(ValueError):pass


def inspect_import(data,root):
    if len(data)>COMPRESSED_LIMIT:raise StoreError(413,'IMPORT_TOO_LARGE','ZIP exceeds the 32 MiB upload limit.')
    root=Path(root).resolve()
    destination=root/'imports'/new_id('import')
    created=False
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries=archive.infolist()
            names=[e.filename for e in entries]
            if len(entries)>ENTRY_LIMIT:raise ImportSizeError('ZIP entry count exceeds the limit.')
            if not entries or len({n.casefold() for n in names})!=len(names):raise ValueError('Invalid or duplicate ZIP entries.')
            total=0
            for entry in entries:
                name=entry.filename
                if not re.fullmatch(r'(?:[a-z0-9][a-z0-9_.-]*/)*[a-z0-9][a-z0-9_.-]*',name) or '..' in PurePosixPath(name).parts or ':' in name or '\\' in name:
                    raise ValueError('Unsafe ZIP path.')
                mode=entry.external_attr>>16
                if entry.is_dir() or stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0,stat.S_IFREG)) or entry.flag_bits&1:raise ValueError('Unsupported ZIP entry type.')
                total+=entry.file_size
                if entry.file_size>FILE_LIMIT or total>EXPANDED_LIMIT or entry.file_size>max(entry.compress_size,1)*200:raise ImportSizeError('ZIP expansion exceeds limits.')
            if 'manifest.json' not in names:raise ValueError('Project manifest is required.')
            if archive.getinfo('manifest.json').file_size>256*1024 or ('project.json' in names and archive.getinfo('project.json').file_size>256*1024):raise ImportSizeError('Manifest or canonical project exceeds size limit.')
            manifest=json.loads(archive.read('manifest.json'))
            import jsonschema
            from woodwork.cad_adapter.runtime import SCHEMA
            jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text())).validate(manifest)
            required={'manifest.json',*[r['relative_path'] for r in manifest['artifacts']]}
            if set(names)!=required:raise ValueError('Unexpected file or incomplete inventory.')
            for record in manifest['artifacts']:
                extension=EXTENSIONS.get(record['kind'])
                if extension is None or PurePosixPath(record['relative_path']).suffix!=extension:raise ValueError('Unexpected executable or file format.')
            parent=destination.parent
            if parent.is_symlink() or (hasattr(parent,'is_junction') and parent.is_junction()):raise ValueError('Import storage cannot be a filesystem link.')
            destination.mkdir(parents=True)
            created=True
            for entry in entries:
                target=destination/entry.filename
                target.parent.mkdir(parents=True,exist_ok=True)
                with target.open('xb') as stream:stream.write(archive.read(entry))
        spec=json.loads((destination/'project.json').read_text())
        resolved=compile_design(spec)
        validate_artifact_set(destination,inspect_geometry=False)
        if hash_json(spec)!=manifest['spec_sha256']:raise ValueError('Imported specification hash differs.')
        # No imported STEP/GLB is parsed by a kernel or served as verified local geometry.
        provenance={'source_project_id':manifest['project_id'],'source_revision_id':manifest['revision_id'],'source_artifact_set_id':manifest['artifact_set_id'],'source_spec_sha256':manifest['spec_sha256'],'source_manifest_sha256':sha256_file(destination/'manifest.json'),'source_zip_sha256':__import__('hashlib').sha256(data).hexdigest()}
        token=destination.name
        write_json(destination/'validation-receipt.json',{'token':token,'spec':resolved['spec'],'provenance':provenance})
        return {'token':token,'status':'validated','rebuild_supported':True,'spec':resolved['spec'],'provenance':provenance,'imported_artifacts':'inert_validated_inventory; trusted_local_rebuild_required','limits':{'compressed_bytes':COMPRESSED_LIMIT,'expanded_bytes':EXPANDED_LIMIT,'entries':ENTRY_LIMIT}}
    except (ValueError,KeyError,OSError,zipfile.BadZipFile,RuntimeError,__import__('jsonschema').ValidationError) as error:
        if created and destination.exists() and not destination.is_symlink() and not destination.is_junction() and destination.resolve().is_relative_to(root/'imports'):
            try:shutil.rmtree(destination)
            except OSError:pass
        if isinstance(error,ImportSizeError):raise StoreError(413,'IMPORT_TOO_LARGE','ZIP expansion exceeds the documented size limits.') from None
        if isinstance(error,DomainError):raise StoreError(422,'IMPORT_SPEC_UNSUPPORTED','The imported project does not match an installed supported contract.',details={'findings':error.findings}) from None
        if isinstance(error,__import__('jsonschema').ValidationError):raise StoreError(422,'IMPORT_SCHEMA_UNSUPPORTED','The imported manifest does not match schema 1.0.0.') from None
        if isinstance(error,OSError):
            try:
                import traceback
                (root/'import-diagnostic.txt').write_text(traceback.format_exc()[-65536:],encoding='utf-8')
            except OSError:pass
            raise StoreError(500,'IMPORT_STORAGE_FAILED','The local store could not retain the upload. Check its disk space and permissions.') from None
        raise StoreError(400,'IMPORT_INVALID','The ZIP failed inert path, file, inventory or integrity validation.') from None


def accept_import(store,token,title):
    if not isinstance(token,str) or not re.fullmatch(r'import_[0-9a-f]{32}',token):raise StoreError(422,'IMPORT_TOKEN_INVALID','Validate the ZIP before importing it.')
    from woodwork.storage.paths import contained_file
    receipt=contained_file(store.root,'imports/'+token+'/validation-receipt.json')
    value=json.loads(receipt.read_text())
    validate_artifact_set(receipt.parent,inspect_geometry=False)
    if sha256_file(receipt.parent/'manifest.json')!=value['provenance']['source_manifest_sha256']:raise StoreError(409,'IMPORT_CHANGED','The validated import has changed. Validate it again.')
    if hash_json(value['spec'])!=value['provenance']['source_spec_sha256']:raise StoreError(409,'IMPORT_CHANGED','The validated specification has changed.')
    return store.create_project(title,value['spec'],provenance=value['provenance'])
