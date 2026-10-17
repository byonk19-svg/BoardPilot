import json
import os
from pathlib import Path
import subprocess
import uuid

import pytest
from pypdf import PdfReader

from woodwork.domain import compile_project
from woodwork.exports.documents import Packet, add_documents, validate_documents
from woodwork.exports.dimensions import format_dual
from woodwork.recipes import RECIPE_ID, RECIPE_VERSION, installed_catalog, resolve_recipe

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "handoff/package/woodworking-codex-handoff/examples"
EXPECTED = json.loads((EXAMPLES / "bookcase-expected.json").read_text())["fixtures"]
RUN_DOCS = os.environ.get("WOODWORK_RUN_DOCUMENT_CORPUS") == "1"
POPPLER = Path(r"C:\Users\byonk\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe")


def test_dual_units_are_real_conversions():
    assert format_dual("25.4") == "1 in (25.4 mm)"
    assert format_dual("18").startswith("approx. ")


def test_application_a4_layout_only_keeps_values_revision_and_part_names(tmp_path):
    """Layout unit check; this does not claim saved-CAD/native-drawing acceptance."""
    spec = json.loads((EXAMPLES / "bookcase-4-shelves.json").read_text())
    spec["documents"]["paper_size"] = "a4"
    ledger = compile_project(spec)
    measured = {"instances": [{"instance_id": i["instance_id"], "world_aabb_mm": {key: [float(i["world_aabb_mm"][key][axis]) for axis in "xyz"] for key in ("min", "max")}} for i in ledger["part_instances"]]}
    metadata = {"revision_id": "a4-layout-unit-check", "revision_number": 1, "spec_sha256": ledger["spec_sha256"], "source_artifact_set_id": "layout-only-no-cad"}
    output = tmp_path / "layout-only.pdf"
    pages = Packet(output, spec, ledger, metadata, measured, resolve_recipe(spec, ledger)).save()
    reader = PdfReader(output)
    text = " ".join("\n".join(p.extract_text() for p in reader.pages).split())
    assert pages == len(reader.pages) == 7
    assert float(reader.pages[0].mediabox.width) == pytest.approx(595.2756, abs=.01)
    assert "a4-layout-unit-check" in text and ledger["spec_sha256"] in text
    assert all(i["instance_id"] in text for i in ledger["part_instances"])
    assert "RECIPE UNSELECTED" in text and "1 in (25.4 mm)" in text


def test_authored_recipe_packet_layout_only_keeps_review_and_purchase_limits(tmp_path):
    """Renderer-only preview; complete genuine selected CAD is a separate gate."""
    spec = json.loads((EXAMPLES / "bookcase-baseline.json").read_text())
    spec["project_name"] = "Layout preview - genuine selected CAD gate still required"
    spec["dimensions"]["outside_depth_mm"] = "355.6"
    spec["materials"]["main"]["actual_thickness_mm"] = "19.05"
    spec["materials"]["back"]["actual_thickness_mm"] = "6.35"
    spec["construction"]["recipe"] = {"id": RECIPE_ID, "version": RECIPE_VERSION}
    spec["documents"]["paper_size"] = "a4"
    ledger = compile_project(spec, recipe_catalog=installed_catalog())
    measured = {"instances": [{"instance_id": i["instance_id"], "world_aabb_mm": {key: [float(i["world_aabb_mm"][key][axis]) for axis in "xyz"] for key in ("min", "max")}} for i in ledger["part_instances"]]}
    metadata = {"revision_id": "authored-layout-unit-check", "revision_number": 1, "spec_sha256": ledger["spec_sha256"], "source_artifact_set_id": "layout-only-no-cad"}
    output = tmp_path / "authored-layout-only.pdf"
    count = Packet(output, spec, ledger, metadata, measured, resolve_recipe(spec, ledger)).save()
    reader = PdfReader(output)
    text = " ".join("\n".join(p.extract_text() for p in reader.pages).split())
    assert count == len(reader.pages) and count >= 11
    assert "PHYSICAL REVIEW PENDING" in text and "NOT REVIEWED" in text
    assert "purchase quantity unknown" in text and "100 purchased in 1 pack" in text
    assert "22.225 mm" in text and "327.025 mm" in text
    assert "not a native section/detail view" in text
    assert "site-specific tip-over restraint" in text


@pytest.fixture(scope="session")
def document_root():
    directory = Path(os.environ.get("WOODWORK_DOCUMENT_CORPUS_ROOT", str(Path(os.environ.get("LOCALAPPDATA", str(ROOT))) / "WoodworkingPlanner" / "m3-documents" / uuid.uuid4().hex)))
    directory.mkdir(parents=True, exist_ok=True)
    return directory


@pytest.mark.skipif(not RUN_DOCS, reason="Set WOODWORK_RUN_DOCUMENT_CORPUS=1 with verified geometry corpus")
@pytest.mark.parametrize("expected", EXPECTED, ids=[e["input_file"] for e in EXPECTED])
def test_genuine_document_fixture_corpus(expected, document_root):
    geometry_root = Path(os.environ["WOODWORK_GEOMETRY_CORPUS_ROOT"])
    stem = expected["input_file"].removesuffix(".json")
    source = geometry_root / stem
    source_manifest = json.loads((source / "manifest.json").read_text())
    spec = json.loads((source / "project.json").read_text())
    resolved = json.loads((source / "resolved-project.json").read_text())
    metadata = {key: source_manifest[key] for key in ("project_id", "revision_id", "revision_number")}
    output = document_root / stem
    result = add_documents(source, output, metadata, spec, resolved)
    assert {"geometry", "documents"} <= set(result["capabilities"])
    assert result["source_artifact_set_id"] == source_manifest["artifact_set_id"]
    assert result["construction"]["status"] == "recipe_unselected"
    assert result["validation"]["documents"] == "passed"
    assert (output / "assembly.step").read_bytes() == (source / "assembly.step").read_bytes()
    evidence = validate_documents(output, spec, resolved, {**metadata, "spec_sha256": source_manifest["spec_sha256"]})
    assert len(evidence["pdfs"]) == 4
    render = document_root / "rendered" / stem
    render.mkdir(parents=True, exist_ok=True)
    for pdf in evidence["pdfs"]:
        prefix = render / Path(pdf["path"]).stem
        subprocess.run([str(POPPLER), "-png", "-r", "100", str(output / pdf["path"]), str(prefix)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    assert len(list(render.glob("*.png"))) == sum(p["pages"] for p in evidence["pdfs"])
    print(f"Rendered every PDF page: {stem} -> {render}")
