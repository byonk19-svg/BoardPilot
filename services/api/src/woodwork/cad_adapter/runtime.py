"""Build fresh staging outputs. The coordinator owns process supervision/publication."""
import csv
import codecs
from collections import deque
import hashlib
import json
import os
import platform
import re
import runpy
import shutil
import subprocess
import sys
import uuid
from importlib.metadata import version
from pathlib import Path

import jsonschema

from woodwork.exports.core import CORE_EXPORT_VERSION, CUT_COLUMNS, artifact_record, canonical_bytes, safe_csv_text, sha256_file, write_core_records, write_json, machining_summary
from .verifier import CadValidationError, measure_geometry, require, validate_ledger

ADAPTER_VERSION = "1.1.0"
REPOSITORY = Path(__file__).resolve().parents[5]
DRIVERS = Path(__file__).resolve().parent / "drivers"
SCHEMA = REPOSITORY / "handoff/package/woodworking-codex-handoff/spec/artifact-manifest.schema.json"
LOCK = REPOSITORY / "requirements-runtime.lock"
DEFINITION_FIELDS = ("definition_id", "material_id", "manufacturing_sha256", "quantity", "finished_mm", "rough_mm", "grain_axis", "member_instance_ids")
INSTANCE_FIELDS = ("instance_id", "definition_id", "center_mm", "rotation_cad_rows")
COORDINATES = {"cad_units": "mm", "cad_axes": "x_width_y_depth_z_height", "part_origin": "center", "part_axes": "x_length_y_width_z_thickness", "preview_units": "m", "cad_to_preview": "x_z_neg_y_times_0.001"}


def construction_manifest(spec,resolved):
    status=resolved['construction_status']
    if status!='recipe_unselected':status=status.removeprefix('recipe_')
    selection=spec['construction']['recipe']
    return {'status':status,'recipe_id':selection['id'] if selection else None,'recipe_version':selection['version'] if selection else None,'physical_review':'not_reviewed','findings':[f['message'] if isinstance(f,dict) else f for f in resolved['construction'].get('findings',[])]}


def _cad_environment(root: Path):
    """Do not forward provider keys, arbitrary PYTHONPATH, or user CAD configuration."""
    # Python falls back to these architecture values when Windows WMI is unavailable.
    # cadgen uses platform.machine() to select its bundled native file tracer.
    environment = {key: os.environ[key] for key in ("SystemRoot", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERPROFILE", "LOCALAPPDATA", "APPDATA", "PROCESSOR_ARCHITECTURE", "PROCESSOR_ARCHITEW6432") if key in os.environ}
    node = Path(os.environ.get("CADGEN_NODE", r"C:\Program Files\nodejs\node.exe")) if os.name == "nt" else Path(shutil.which("node") or "/usr/bin/node")
    require(node.is_file(), "Approved Node runtime unavailable")
    environment.update({
        "PATH": os.pathsep.join([str(Path(sys.executable).parent), str(node.parent), os.path.join(environment.get("SystemRoot", environment.get("SYSTEMROOT", "C:\\Windows")), "System32")]) if os.name == "nt" else os.defpath,
        "CADGEN_DAEMON": "0", "CADGEN_JOBS": "1", "CADGEN_TELEMETRY": "0", "CADGEN_UPDATE_CHECK": "0", "CADGEN_NODE": str(node),
        "CADGEN_CACHE_DIR": os.environ.get("CADGEN_CACHE_DIR", str(root / "cache")),
        "CADGEN_STATE_DIR": os.environ.get("CADGEN_STATE_DIR", str(root / "state")),
        "MPLCONFIGDIR": os.environ.get("MPLCONFIGDIR", str(root / "matplotlib")),
        "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8",
        "PYTHONPATH": str(DRIVERS.parent/'native_bootstrap'),
    })
    return environment


def _versions(spec, resolved, environment):
    node = subprocess.run([environment["CADGEN_NODE"], "--version"], shell=False, env=environment, capture_output=True, text=True, encoding="utf-8", check=True, timeout=10).stdout.strip().lstrip("v")
    require(version("cadgen") == "0.7.21" and sys.version_info[:2] == (3, 13), "Pinned CAD/Python runtime mismatch")
    require(version("build123d") == "0.11.1" and version("cadquery-ocp-novtk") == "7.9.3.1.1", "Pinned native CAD dependency mismatch")
    require(node == "24.13.0", "Selected Node runtime version mismatch")
    return {"app": "0.1.0", "template": spec["template"]["version"], "compiler": resolved["compiler_version"], "adapter": ADAPTER_VERSION,
            "cadgen": version("cadgen"), "python": platform.python_version(), "build123d": version("build123d"), "ocp": version("cadquery-ocp-novtk"),
            "node": node, "dependency_lock_sha256": sha256_file(LOCK), "recipe_fingerprint": resolved['construction'].get('fingerprint')}


def _build_inputs(spec, resolved, versions):
    return {"spec_sha256": resolved["spec_sha256"], "resolved_sha256": resolved["resolved_sha256"], "template": spec["template"], "recipe_fingerprint": versions["recipe_fingerprint"],
            "compiler_version": versions["compiler"], "adapter_version": ADAPTER_VERSION, "dependency_lock_sha256": versions["dependency_lock_sha256"],
            "cadgen_upstream_commit": "24573128ceaab564f497d7c12f995c41784c9539", "toolchain_versions": {key: versions[key] for key in ("cadgen", "python", "build123d", "ocp", "node")},
            "core_export_version": CORE_EXPORT_VERSION, "export_options": {"geometry": "step_and_per_definition_glb", "documents": None},
            "source_sha256": {name:sha256_file(REPOSITORY/'services/api/src/woodwork'/name) for name in ('application.py','domain/compiler.py','templates/bookcase.py','exports/core.py','cad_adapter/runtime.py','cad_adapter/verifier.py','cad_adapter/windows_runtime.py','cad_adapter/native_bootstrap/sitecustomize.py')},
            "driver_sha256": {name: sha256_file(DRIVERS / name) for name in ("part.py", "assembly.py", "batch.py")}}


DRIVER_STAGES = {'generating_side_panels','generating_horizontal_panels','generating_back_panel','assembling_geometry'}


def _run_driver(driver: Path, environment, *, progress=None):
    # The app coordinator starts this adapter in a contained OS process. Descendants
    # inherit its Job Object/process group. Deadline/cancellation belongs to that
    # supervisor; an immediate-PID-only timeout here would leave Node descendants.
    process = subprocess.Popen([sys.executable, "-u", str(driver)], shell=False, cwd=driver.parent, env=environment,
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    retained = deque(maxlen=16)  # At most 64 KiB retained; continuously drain the pipe.
    assert process.stderr is not None
    decoder=codecs.getincrementaldecoder('utf-8')('replace')
    pending=''; discard=False
    with process.stderr:
        while chunk := os.read(process.stderr.fileno(),4096):
            retained.append(chunk)
            for character in decoder.decode(chunk):
                if character=='\n':
                    if not discard and progress:
                        try: value=json.loads(pending)
                        except ValueError: value=None
                        stage=value.get('woodwork_stage') if isinstance(value,dict) else None
                        if isinstance(stage,str) and stage in DRIVER_STAGES:
                            progress(stage)
                    pending=''; discard=False
                elif not discard:
                    pending+=character
                    if len(pending)>16384: pending=''; discard=True
    code = process.wait()
    if code:
        (driver.parent / "failure-stderr.txt").write_bytes(b"".join(retained))
        # Raw upstream diagnostics may include local paths. Keep the public error safe.
        raise CadValidationError(f"Native CAD driver failed with exit code {code}")


def _run_owned_driver(driver: Path, environment, *, progress=None):
    """Share the kernel only inside the coordinator's isolated single-job worker.

    No daemon or long-lived API process executes CAD. All descendants remain in
    the worker's OS containment, with the same cancellation and wall deadline.
    """
    previous_environment=dict(os.environ); previous_argv=sys.argv; previous_cwd=Path.cwd()
    def forward(stage):
        if isinstance(stage,str) and stage in DRIVER_STAGES and progress:
            progress(stage)
    try:
        os.environ.clear(); os.environ.update(environment)
        os.chdir(driver.parent); sys.argv=[str(driver)]
        if os.name=='nt':
            runpy.run_path(str(DRIVERS.parent/'native_bootstrap/sitecustomize.py'))
        try:
            runpy.run_path(str(driver),run_name='__main__',init_globals={'WOODWORK_PROGRESS':forward})
        except SystemExit as error:
            if error.code not in (None,0):
                raise CadValidationError(f'Native CAD driver failed with exit code {error.code}') from error
    finally:
        sys.argv=previous_argv; os.chdir(previous_cwd)
        os.environ.clear(); os.environ.update(previous_environment)


def build_artifact_set(spec: dict, resolved: dict, metadata: dict, out_dir: Path | str, *, progress=None, owned_process=False):
    """Return verified geometry manifest, leaving a fresh, unpublished staging set."""
    out_dir = Path(out_dir).resolve()
    require(not out_dir.exists() or not any(out_dir.iterdir()), "CAD staging directory must be new and empty")
    validate_ledger(spec, resolved)
    metadata = dict(metadata)
    for name in ("project_id", "revision_id", "revision_number"):
        require(name in metadata, "Missing revision metadata")
    require(type(metadata["revision_number"]) is int and metadata["revision_number"] >= 1, "Invalid revision number")
    require(metadata.get("spec_sha256", resolved["spec_sha256"]) == resolved["spec_sha256"], "Revision spec checksum mismatch")
    require(metadata.get("resolved_sha256", resolved["resolved_sha256"]) == resolved["resolved_sha256"], "Revision ledger checksum mismatch")
    metadata["spec_sha256"] = resolved["spec_sha256"]
    metadata["resolved_sha256"] = resolved["resolved_sha256"]
    out_dir.mkdir(parents=True, exist_ok=True)
    work = out_dir / ".work"
    work.mkdir()
    environment = _cad_environment(work)
    versions = _versions(spec, resolved, environment)
    inputs = _build_inputs(spec, resolved, versions)
    build_key = hashlib.sha256(canonical_bytes(inputs)).hexdigest()
    require(metadata.get("build_key_sha256", build_key) == build_key, "Build input fingerprint mismatch")
    write_core_records(out_dir, spec, resolved, metadata)
    (out_dir / "parts").mkdir()
    if progress:
        progress("generating_geometry")
    for definition in resolved["part_definitions"]:
        definition_id = definition["definition_id"]
        directory = work / definition_id
        directory.mkdir()
        shutil.copyfile(DRIVERS / "part.py", directory / "part.py")
        write_json(directory / "part.json", definition["finished_mm"])
    directory = work / "assembly"
    directory.mkdir()
    shutil.copyfile(DRIVERS / "assembly.py", directory / "assembly.py")
    write_json(directory / "assembly.json", {"part_definitions": resolved["part_definitions"], "part_instances": resolved["part_instances"]})
    shutil.copyfile(DRIVERS/'batch.py',work/'batch.py')
    write_json(work/'batch.json',{'definition_ids':[d['definition_id'] for d in resolved['part_definitions']]})
    runner=_run_owned_driver if owned_process else _run_driver
    runner(work/'batch.py',environment,progress=progress)
    timings=json.loads((work/'timings.json').read_text(encoding='utf-8'))
    # Inspection reopens the saved bytes independently of the model bodies. Owned
    # workers reuse their imported kernel; library callers retain a child driver.
    if progress:
        progress("inspecting_geometry")
    report, mapping = measure_geometry(out_dir, resolved)
    report.update({"revision_id": metadata["revision_id"], "spec_sha256": metadata["spec_sha256"], "resolved_sha256": metadata["resolved_sha256"], "timings": timings})
    write_json(out_dir / "geometry-validation.json", report)
    write_json(out_dir / "build-inputs.json", inputs)
    assembly_record = artifact_record(out_dir, "assembly.step", "step", "model/step", metadata)
    write_json(out_dir / "step-instance-map.json", {"schema_version": "1.0.0", "revision_id": metadata["revision_id"], "spec_sha256": metadata["spec_sha256"], "resolved_sha256": metadata["resolved_sha256"],
                                                "assembly_artifact_id": assembly_record["artifact_id"], "assembly_sha256": assembly_record["sha256"], "instances": mapping})
    records = [assembly_record]
    for definition in resolved["part_definitions"]:
        for kind, mime in (("step", "model/step"), ("glb", "model/gltf-binary")):
            records.append(artifact_record(out_dir, f"parts/{definition['definition_id']}.{kind}", kind, mime, metadata, definition["definition_id"]))
    for name in ("project.json", "resolved-project.json", "materials.json", "geometry-validation.json", "build-inputs.json", "step-instance-map.json"):
        records.append(artifact_record(out_dir, name, "json", "application/json", metadata))
    records.extend([artifact_record(out_dir, "cut-list.csv", "csv", "text/csv; charset=utf-8", metadata), artifact_record(out_dir, "readme.txt", "text", "text/plain; charset=utf-8", metadata)])
    manifest = {
        "manifest_schema_version": "1.0.0", "project_id": metadata["project_id"], "revision_id": metadata["revision_id"], "revision_number": metadata["revision_number"],
        "spec_sha256": metadata["spec_sha256"], "resolved_sha256": metadata["resolved_sha256"], "build_key_sha256": build_key, "versions": versions, "coordinates": COORDINATES,
        "part_definitions": [{key: definition[key] for key in DEFINITION_FIELDS} for definition in resolved["part_definitions"]],
        "part_instances": [{key: instance[key] for key in INSTANCE_FIELDS} for instance in resolved["part_instances"]], "artifacts": records,
        "validation": {"parameters": "passed", "geometry": "passed", "documents": "not_requested", "stock_layout": "not_requested"},
        "construction": construction_manifest(spec,resolved),
        "artifact_set_id": metadata.get("artifact_set_id", str(uuid.uuid4())), "source_artifact_set_id": None, "capabilities": ["geometry"],
    }
    jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(manifest)
    write_json(out_dir / "manifest.json", manifest)
    # Work caches are disposable and were created only inside this empty staging set.
    require(work.resolve().parent == out_dir, "Unexpected work directory containment")
    shutil.rmtree(work)
    validate_artifact_set(out_dir, inspect_geometry=False)
    return manifest


def _safe_artifact_path(root, relative):
    require(isinstance(relative, str) and re.fullmatch(r"(?:[a-z0-9][a-z0-9_.-]*/)*[a-z0-9][a-z0-9_.-]*", relative), "Unsafe artifact path")
    path = root / relative
    require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root), "Missing or escaped artifact")
    require(all(not parent.is_symlink() for parent in path.parents if parent != root and parent.is_relative_to(root)), "Symlink artifact directory forbidden")
    return path


def validate_artifact_set(out_dir: Path | str, inspect_geometry=True):
    """Verify manifest inventory, saved CAD, CSV and revision bindings independently."""
    from woodwork.domain import hash_json

    root = Path(out_dir).resolve()
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(manifest)
    records = manifest["artifacts"]
    require(len({r["artifact_id"] for r in records}) == len(records) and len({r["relative_path"] for r in records}) == len(records), "Duplicate artifact inventory identity")
    for record in records:
        path = _safe_artifact_path(root, record["relative_path"])
        require(path.stat().st_size == record["size_bytes"] and sha256_file(path) == record["sha256"], "Artifact byte integrity mismatch")
        require(record["revision_id"] == manifest["revision_id"] and record["spec_sha256"] == manifest["spec_sha256"], "Mixed artifact revision identity")
    by_path = {r["relative_path"]: r for r in records}
    definition_ids = {d["definition_id"] for d in manifest["part_definitions"]}
    require(all(r["definition_id"] is None or r["definition_id"] in definition_ids for r in records), "Artifact references unknown definition")
    required = {"project.json", "resolved-project.json", "assembly.step", "cut-list.csv", "step-instance-map.json", "geometry-validation.json", "build-inputs.json", "materials.json", "readme.txt"}
    for definition in manifest["part_definitions"]:
        for kind in ("step", "glb"):
            required.add(f"parts/{definition['definition_id']}.{kind}")
        for kind in ("step", "glb"):
            matches = [r for r in records if r["definition_id"] == definition["definition_id"] and r["kind"] == kind]
            require(len(matches) == 1 and matches[0]["relative_path"] == f"parts/{definition['definition_id']}.{kind}", "Missing or duplicate maintained definition artifact")
    require(required <= set(by_path), "Incomplete core geometry artifact set")
    require(len([r for r in records if r["kind"] == "step" and r["definition_id"] is None]) == 1, "Missing or duplicate assembly STEP")
    spec = json.loads((root / "project.json").read_text(encoding="utf-8"))
    resolved = json.loads((root / "resolved-project.json").read_text(encoding="utf-8"))
    validate_ledger(spec, resolved)
    require(manifest["spec_sha256"] == resolved["spec_sha256"] and manifest["resolved_sha256"] == resolved["resolved_sha256"], "Manifest source hash mismatch")
    construction=construction_manifest(spec,resolved)
    require(all(manifest['construction'][key]==construction[key] for key in ('status','recipe_id','recipe_version','physical_review')), 'Manifest construction claims disagree with trusted recipe')
    require(manifest['versions']['recipe_fingerprint']==resolved['construction'].get('fingerprint'), 'Manifest recipe fingerprint mismatch')
    require(manifest["part_definitions"] == [{key: definition[key] for key in DEFINITION_FIELDS} for definition in resolved["part_definitions"]], "Manifest manufacturing ledger mismatch")
    require(manifest["part_instances"] == [{key: instance[key] for key in INSTANCE_FIELDS} for instance in resolved["part_instances"]], "Manifest instance ledger mismatch")
    inputs = json.loads((root / "build-inputs.json").read_text(encoding="utf-8"))
    require(hash_json(inputs) == manifest["build_key_sha256"] and inputs["spec_sha256"] == manifest["spec_sha256"] and inputs["resolved_sha256"] == manifest["resolved_sha256"], "Build key source mismatch")
    sidecar = json.loads((root / "step-instance-map.json").read_text(encoding="utf-8"))
    assembly = by_path["assembly.step"]
    require(sidecar["schema_version"] == "1.0.0" and sidecar["revision_id"] == manifest["revision_id"] and sidecar["spec_sha256"] == manifest["spec_sha256"] and sidecar["resolved_sha256"] == manifest["resolved_sha256"], "STEP map revision binding mismatch")
    require(sidecar["assembly_artifact_id"] == assembly["artifact_id"] and sidecar["assembly_sha256"] == assembly["sha256"], "STEP map assembly hash binding mismatch")
    mapping = sidecar["instances"]
    ids = {i["instance_id"] for i in resolved["part_instances"]}
    require(len(mapping) == len(ids) and {i["instance_id"] for i in mapping} == ids and len({i["selector"] for i in mapping}) == len(mapping), "STEP map coverage mismatch")
    require(all(i["instance_id"] == i["occurrence_label"] for i in mapping), "STEP map label mismatch")
    with (root / "cut-list.csv").open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = tuple(reader.fieldnames or ())
        require(fields in (CUT_COLUMNS, CUT_COLUMNS + ("definition_ids",)), "CSV schema mismatch")
        rows = list(reader)
    require(len(rows) == len(resolved["cut_groups"]), "CSV group cardinality mismatch")
    require(len({row["cut_group_id"] for row in rows}) == len(rows), "Duplicate CSV manufacturing cut group")
    for row, definition in zip(rows, resolved["cut_groups"]):
        require(row["revision_id"] == safe_csv_text(manifest["revision_id"]) and row["spec_sha256"] == manifest["spec_sha256"], "CSV revision identity mismatch")
        expected = {"cut_group_id": definition["manufacturing_sha256"], "definition_id": definition["definition_id"], "quantity": str(definition["quantity"]), "member_instance_ids": ";".join(definition["member_instance_ids"]), "material_id": safe_csv_text(definition["material_id"]), "actual_thickness_mm": definition["finished_mm"]["thickness_mm"], "finished_length_mm": definition["finished_mm"]["length_mm"], "finished_width_mm": definition["finished_mm"]["width_mm"], "rough_length_mm": definition["rough_mm"]["length_mm"], "rough_width_mm": definition["rough_mm"]["width_mm"], "grain_axis": definition["grain_axis"]}
        require(all(row[key] == value for key, value in expected.items()), "CSV manufacturing dimensions disagree with revision")
        require(row['machining_summary'] == machining_summary(definition), 'CSV planned operations disagree with revision')
        if "definition_ids" in fields:
            require(row["definition_ids"] == ";".join(definition["definition_ids"]), "CSV group definition membership mismatch")
        else:
            require(len(definition["definition_ids"]) == 1, "Merged CSV group must explicitly identify definition membership")
    materials = json.loads((root / "materials.json").read_text(encoding="utf-8"))
    require(materials["revision_id"] == manifest["revision_id"] and materials["spec_sha256"] == manifest["spec_sha256"] and materials["materials"] == spec["materials"], "Materials source binding mismatch")
    require(materials.get('hardware',[])==resolved.get('construction_recipe',{}).get('hardware',[]), 'Materials hardware differs from trusted recipe')
    evidence = json.loads((root / "geometry-validation.json").read_text(encoding="utf-8"))
    require(evidence["revision_id"] == manifest["revision_id"] and evidence["spec_sha256"] == manifest["spec_sha256"] and evidence["resolved_sha256"] == manifest["resolved_sha256"] and evidence["geometry"] == "passed", "Geometry report revision mismatch")
    inspected=evidence.get('cad_artifact_sha256')
    if inspected is not None or manifest['versions']['adapter']!='1.0.0':
        expected_bytes={r['relative_path']:r['sha256'] for r in records if r['kind'] in {'step','glb'}}
        require(inspected==expected_bytes,'Native inspection does not bind these saved CAD bytes')
        inspected_mapping=sorted([{'instance_id':item['instance_id'],'occurrence_label':item['instance_id'],'selector':item['selector']} for item in evidence.get('instances',[])],key=lambda item:item['instance_id'])
        require(mapping==inspected_mapping,'Native inspection does not bind these saved STEP selectors')
    if inspect_geometry:
        report, saved_mapping = measure_geometry(root, resolved)
        require(mapping == saved_mapping, "STEP selectors no longer resolve the stated occurrences")
    else:
        report = evidence
    if 'documents' in manifest['capabilities']:
        from woodwork.exports.documents import validate_documents
        document_inputs=inputs
        for _ in range(20):
            if 'documents_version' in document_inputs:break
            document_inputs=document_inputs.get('source_inputs',document_inputs.get('geometry_inputs',{}))
        require('documents_version' in document_inputs and document_inputs['document_options']==spec['documents'],'Document build provenance or options missing')
        document_source=document_inputs.get('source_artifact_set_id')
        require(isinstance(document_source,str),'Document generation source identity missing')
        validate_documents(root,spec,resolved,{**manifest,'source_artifact_set_id':document_source})
        recipe_record=json.loads((root/'construction-recipe.json').read_text(encoding='utf-8'))
        from woodwork.recipes import resolve_recipe
        expected_recipe=resolve_recipe(spec,resolved)
        require(all(recipe_record.get(k)==v for k,v in expected_recipe.items()), 'Document recipe differs from trusted installed construction method')
        require(all(recipe_record[k]==manifest[k] for k in ('revision_id','spec_sha256','resolved_sha256')), 'Document recipe source binding mismatch')
    if 'stock_layout' in manifest['capabilities']:
        from woodwork.exports.stock import validate_stock_output
        stock_evidence=validate_stock_output(root,spec,resolved,manifest)
        require(manifest['validation']['stock_layout']==('passed' if stock_evidence['layout_status']=='complete' else 'incomplete'),'Manifest stock completeness disagrees with verified coverage')
    return {"status": "passed", "revision_id": manifest["revision_id"], "artifact_set_id": manifest["artifact_set_id"], "artifact_count": len(records), "geometry": report}
