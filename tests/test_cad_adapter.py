"""M1 genuine native geometry corpus, plus fast artifact-boundary regressions."""
import copy
import csv
import json
import os
import uuid
import sys
from pathlib import Path

import pytest

from woodwork.cad_adapter import CadValidationError, build_artifact_set, validate_artifact_set
from woodwork.cad_adapter.verifier import validate_ledger
from woodwork.domain import compile_project, hash_json, resolved_hash
from woodwork.exports.core import CSV_COLUMNS, CUT_COLUMNS, safe_csv_text, sha256_file, write_cut_list, write_json

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "handoff/package/woodworking-codex-handoff/examples"
EXPECTED = json.loads((EXAMPLES / "bookcase-expected.json").read_text(encoding="utf-8"))["fixtures"]
RUN_CAD = os.environ.get("WOODWORK_RUN_CAD_CORPUS") == "1"


def load_spec(name="bookcase-baseline.json"):
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


def test_compiler_ledger_accepted():
    spec = load_spec()
    validate_ledger(spec, compile_project(spec))


@pytest.mark.parametrize("value", ["=1+1", "+CMD", "-CMD", "@SUM(A1)", "  =2+2", "\tplain", "\rplain"])
def test_spreadsheet_formula_neutralization(value):
    assert safe_csv_text(value) == "'" + value


def test_csv_exact_columns_and_measured_thickness(tmp_path):
    spec = load_spec()
    spec["materials"]["main"]["name"] = "  =HYPERLINK(\"bad\")"
    resolved = compile_project(spec)
    path = tmp_path / "cut.csv"
    write_cut_list(path, spec, resolved, {"revision_id": "r1", "spec_sha256": resolved["spec_sha256"]})
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        assert tuple(reader.fieldnames) == CSV_COLUMNS
        rows = list(reader)
    assert [row["quantity"] for row in rows] == ["2", "4", "1"]
    assert rows[0]["material_name"].startswith("'  =")
    assert rows[0]["actual_thickness_mm"] == "18"
    assert rows[1]["finished_length_mm"] == "726"
    assert rows[1]["member_instance_ids"] == "bottom;shelf_01;shelf_02;top"


def test_full_fingerprint_grouping_merges_equivalent_semantic_definitions(tmp_path):
    spec = load_spec()
    spec["dimensions"]["outside_width_mm"] = "950.4"
    resolved = compile_project(spec)
    path = tmp_path / "grouped.csv"
    write_cut_list(path, spec, resolved, {"revision_id": "r-equivalent", "spec_sha256": resolved["spec_sha256"]})
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(resolved["part_definitions"]) == 3
    assert len(rows) == len(resolved["cut_groups"]) == 2
    assert rows[0]["quantity"] == "6"
    assert rows[0]["definition_id"] == "panel_side"
    assert rows[0]["definition_ids"] == "panel_side;panel_horizontal"
    assert set(rows[0]["member_instance_ids"].split(";")) == {"side_left", "side_right", "bottom", "shelf_01", "shelf_02", "top"}
    assert len({row["cut_group_id"] for row in rows}) == 2


def test_reflection_rejected_even_when_ledger_checksum_updated():
    spec = load_spec()
    resolved = compile_project(spec)
    resolved["part_instances"][0]["rotation_cad_rows"] = [[0, 0, 1], [0, 1, 0], [1, 0, 0]]
    resolved["resolved_sha256"] = resolved_hash(resolved)
    with pytest.raises(CadValidationError, match="Reflected"):
        validate_ledger(spec, resolved)


def test_cross_revision_input_rejected_before_generation(tmp_path):
    spec = load_spec()
    resolved = compile_project(spec)
    spec["dimensions"]["outside_width_mm"] = "914.4"
    with pytest.raises(CadValidationError, match="Spec does not match"):
        build_artifact_set(spec, resolved, {"project_id": "p1", "revision_id": "r1", "revision_number": 1}, tmp_path / "staging")
    assert not (tmp_path / "staging").exists()


def test_unrelated_staging_files_preserved(tmp_path):
    sentinel = tmp_path / "unrelated.txt"
    sentinel.write_text("preserve")
    spec = load_spec()
    with pytest.raises(CadValidationError, match="must be new and empty"):
        build_artifact_set(spec, compile_project(spec), {"project_id": "p1", "revision_id": "r1", "revision_number": 1}, tmp_path)
    assert sentinel.read_text() == "preserve"


@pytest.mark.parametrize("mutation", ["grain", "fingerprint", "thickness", "length"])
def test_rehashed_invented_ledger_rejected(mutation):
    spec = load_spec()
    resolved = compile_project(spec)
    definition = resolved["part_definitions"][0]
    if mutation == "grain":
        definition["grain_axis"] = "none"
    elif mutation == "fingerprint":
        definition["manufacturing_sha256"] = "0" * 64
    elif mutation == "thickness":
        definition["finished_mm"]["thickness_mm"] = "17"
        definition["rough_mm"]["thickness_mm"] = "17"
    else:
        definition["finished_mm"]["length_mm"] = "900"
        definition["rough_mm"]["length_mm"] = "900"
    resolved["resolved_sha256"] = resolved_hash(resolved)
    with pytest.raises(CadValidationError, match="authoritative spec compilation"):
        validate_ledger(spec, resolved)


@pytest.fixture(scope="session")
def corpus_root():
    directory = Path(os.environ.get("WOODWORK_CAD_CORPUS_ROOT", str(Path(os.environ.get("LOCALAPPDATA", str(ROOT))) / "WoodworkingPlanner" / "m1-corpus" / uuid.uuid4().hex)))
    directory.mkdir(parents=True, exist_ok=True)
    return directory


@pytest.mark.skipif(not RUN_CAD, reason="Run WOODWORK_RUN_CAD_CORPUS=1 for genuine saved-CAD acceptance")
@pytest.mark.parametrize("expected", EXPECTED, ids=[entry["input_file"] for entry in EXPECTED])
def test_genuine_cad_fixture_corpus(expected, corpus_root):
    spec = load_spec(expected["input_file"])
    resolved = compile_project(spec)
    fixture_id = expected["input_file"].removesuffix(".json")
    out_dir = corpus_root / fixture_id
    metadata={"project_id": "m1-acceptance", "revision_id": fixture_id, "revision_number": 1}
    if os.environ.get('WOODWORK_CAD_OWNED_CORPUS')=='1':
        from woodwork.jobs.environment import worker_environment
        from woodwork.jobs.process import ProcessSupervisor
        job_root=corpus_root/(fixture_id+'-worker'); job_root.mkdir()
        write_json(job_root/'input.json',{'kind':'generate','spec':spec,'resolved':resolved,'metadata':metadata})
        with ProcessSupervisor() as supervisor:
            result=supervisor.run([sys.executable,'-u','-m','woodwork.jobs.worker',str(job_root)],cwd=ROOT,env=worker_environment(corpus_root),log_path=job_root/'worker.log',timeout_seconds=120)
        write_json(job_root/'process-result.json',{'returncode':result.returncode,'timed_out':result.timed_out,'elapsed_seconds':result.elapsed_seconds,'peak_rss_bytes':result.peak_rss_bytes})
        assert result.returncode==0 and not result.timed_out, f'Owned worker failed; inspect {job_root}'
        (job_root/'out').rename(out_dir)
        manifest=json.loads((out_dir/'manifest.json').read_text(encoding='utf-8'))
    else:
        manifest = build_artifact_set(spec, resolved, metadata, out_dir)
    verified = validate_artifact_set(out_dir)
    geometry = verified["geometry"]
    assert manifest["spec_sha256"] == expected["canonical_spec_sha256"]
    assert manifest["validation"] == {"parameters": "passed", "geometry": "passed", "documents": "not_requested", "stock_layout": "not_requested"}
    assert len(manifest["part_instances"]) == expected["part_instance_count"]
    assert geometry["assembly"]["solid_count"] == expected["part_instance_count"]
    assert geometry["assembly"]["part_volume_mm3"] == pytest.approx(float(expected["total_part_volume_mm3"]), abs=.001)
    assert geometry["assembly"]["union_volume_mm3"] == pytest.approx(float(expected["total_part_volume_mm3"]), abs=.001)
    for extent in ("min", "max"):
        assert geometry["assembly"]["world_aabb_mm"][extent] == pytest.approx([float(expected["world_aabb_mm"][extent][axis]) for axis in "xyz"], abs=.000002)
    by_instance = {item["instance_id"]: item for item in geometry["instances"]}
    for instance in expected["part_instances"]:
        report = by_instance[instance["instance_id"]]
        assert report["center_mm"] == pytest.approx([float(instance["center_mm"][axis]) for axis in "xyz"], abs=.000002)
    assert len(geometry["pair_checks"]) == expected["part_instance_count"] * (expected["part_instance_count"] - 1) // 2
    assert all(item["overlap_volume_mm3"] <= .000001 for item in geometry["pair_checks"])
    assert all(item["solid_count"] == 1 and item["glb_vertex_count"] > 0 for item in geometry["definitions"])
    assert manifest["construction"]["status"] == "recipe_unselected"
    assert manifest["construction"]["physical_review"] == "not_reviewed"
    assert all(item["sha256"] == sha256_file(out_dir / item["relative_path"]) for item in manifest["artifacts"])
    assert len([item for item in manifest["artifacts"] if item["kind"] == "step"]) == 4
    assert len([item for item in manifest["artifacts"] if item["kind"] == "glb"]) == 3
    print(f"CAD fixture verified: {out_dir}")


@pytest.mark.skipif(not RUN_CAD, reason="Requires generated native baseline corpus")
def test_tampered_artifact_bytes_rejected(corpus_root, tmp_path):
    import shutil
    original = corpus_root / "bookcase-baseline"
    assert original.exists(), "Run after the baseline corpus case"
    target = tmp_path / "tampered"
    shutil.copytree(original, target)
    with (target / "parts/panel_horizontal.step").open("ab") as stream:
        stream.write(b"tamper")
    with pytest.raises(CadValidationError, match="byte integrity"):
        validate_artifact_set(target, inspect_geometry=False)


@pytest.mark.skipif(not RUN_CAD, reason="Requires generated native baseline corpus")
def test_semantic_mixed_revision_csv_rejected(corpus_root, tmp_path):
    import shutil
    original = corpus_root / "bookcase-baseline"
    assert original.exists(), "Run after the baseline corpus case"
    target = tmp_path / "mixed"
    shutil.copytree(original, target)
    csv_path = target / "cut-list.csv"
    csv_path.write_text(csv_path.read_text(encoding="utf-8").replace(",726,298.8,", ",878.4,298.8,"), encoding="utf-8")
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    artifact = next(item for item in manifest["artifacts"] if item["relative_path"] == "cut-list.csv")
    artifact["sha256"] = sha256_file(csv_path)
    artifact["size_bytes"] = csv_path.stat().st_size
    write_json(target / "manifest.json", manifest)
    with pytest.raises(CadValidationError, match="CSV manufacturing dimensions"):
        validate_artifact_set(target, inspect_geometry=False)


@pytest.mark.skipif(not RUN_CAD, reason='Requires genuine source STEP files for saved overlap injection.')
def test_genuine_saved_material_overlap_is_rejected(corpus_root,tmp_path):
    import shutil
    from cadgen import read_step,build123d as bd
    target=tmp_path/'overlap'
    shutil.copytree(corpus_root/'bookcase-baseline',target)
    resolved=json.loads((target/'resolved-project.json').read_text())
    definitions={d['definition_id']:read_step(target/'parts'/f"{d['definition_id']}.step").solids()[0] for d in resolved['part_definitions']}
    bottom=next(i for i in resolved['part_instances'] if i['instance_id']=='bottom')
    children=[];by_id={}
    for instance in resolved['part_instances']:
        position=bottom['center_mm'] if instance['instance_id']=='shelf_01' else instance['center_mm']
        rotation=instance['rotation_cad_rows']
        plane=bd.Plane(origin=tuple(float(position[a]) for a in 'xyz'),x_dir=tuple(row[0] for row in rotation),z_dir=tuple(row[2] for row in rotation))
        shape=definitions[instance['definition_id']].moved(bd.Location(plane));shape.label=instance['instance_id']
        children.append(shape);by_id[shape.label]=shape
    intersection=by_id['bottom'].intersect(by_id['shelf_01'])
    overlap=sum(s.volume for s in intersection) if intersection else 0
    assert overlap>3_000_000
    bd.export_step(bd.Compound(children=children,label='woodworking_assembly'),target/'assembly.step',unit=bd.Unit.MM)
    manifest=json.loads((target/'manifest.json').read_text())
    assembly=next(a for a in manifest['artifacts'] if a['relative_path']=='assembly.step')
    assembly.update(sha256=sha256_file(target/'assembly.step'),size_bytes=(target/'assembly.step').stat().st_size)
    sidecar=json.loads((target/'step-instance-map.json').read_text());sidecar['assembly_sha256']=assembly['sha256']
    write_json(target/'step-instance-map.json',sidecar)
    mapping=next(a for a in manifest['artifacts'] if a['relative_path']=='step-instance-map.json')
    mapping.update(sha256=sha256_file(target/'step-instance-map.json'),size_bytes=(target/'step-instance-map.json').stat().st_size)
    write_json(target/'manifest.json',manifest)
    # Modern byte bindings reject the changed assembly before native inspection.
    # Also exercise the independent reader itself, so this negative case cannot
    # pass solely because the saved inspection hashes are stale.
    from woodwork.cad_adapter.verifier import measure_geometry
    with pytest.raises(CadValidationError):measure_geometry(target,resolved)
    with pytest.raises(CadValidationError):validate_artifact_set(target,inspect_geometry=True)


@pytest.mark.skipif(not RUN_CAD, reason="Requires native saved-CAD contact-band regression")
def test_quantized_contact_bands_preserve_supported_thickness(corpus_root):
    spec = load_spec()
    spec["materials"]["main"]["actual_thickness_mm"] = "18.000003"
    resolved = compile_project(spec)
    directory = corpus_root / "precision-contact"
    build_artifact_set(spec, resolved, {"project_id": "m1-precision", "revision_id": "r-precision-contact", "revision_number": 1}, directory)
    result = validate_artifact_set(directory)
    geometry = result["geometry"]
    assert result["status"] == "passed"
    assert geometry["assembly"]["numerical_contact_overlap_mm3"] > 0
    assert all(pair["overlap_volume_mm3"] <= pair["overlap_tolerance_mm3"] for pair in geometry["pair_checks"])
    assert all(pair["overlap_volume_mm3"] <= .000001 for pair in geometry["pair_checks"] if not pair["permitted_contact"])
    assert geometry["position_tolerance_mm"] == "2e-06"
