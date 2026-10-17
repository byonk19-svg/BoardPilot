import copy
import json
from pathlib import Path

import pytest

from woodwork.domain import DomainError, compile_project
from woodwork.recipes import RECIPE_ID, RECIPE_VERSION, build_recipe_graph, installed_catalog, public_catalog, resolve_recipe, validate_recipe_graph, manufacturing_plan
from woodwork.domain import canonical_json

ROOT = Path(__file__).resolve().parents[1]


def spec_and_ledger(selected=True, supported=True):
    spec = json.loads((ROOT / "handoff/package/woodworking-codex-handoff/examples/bookcase-baseline.json").read_text())
    if supported:
        spec["dimensions"]["outside_depth_mm"] = "355.6"
        spec["materials"]["main"]["actual_thickness_mm"] = "19.05"
        spec["materials"]["back"]["actual_thickness_mm"] = "6.35"
    if selected:
        spec["construction"]["recipe"] = {"id": RECIPE_ID, "version": RECIPE_VERSION}
    return spec, compile_project(spec, recipe_catalog=installed_catalog())


def test_unselected_stays_design_packet():
    spec, ledger = spec_and_ledger(selected=False, supported=False)
    result = resolve_recipe(spec, ledger)
    assert result["status"] == "recipe_unselected"
    assert not result["operations"] and not result["hardware"]
    assert result["physical_review"] == "not_reviewed"


def test_unknown_recipe_rejected():
    spec, ledger = spec_and_ledger(selected=False)
    spec["construction"]["recipe"] = {"id": "unknown_method", "version": "1.0.0"}
    with pytest.raises(DomainError) as error:
        resolve_recipe(spec, ledger)
    assert error.value.findings[0]["code"] == "RECIPE_UNKNOWN"


def test_actual_18mm_reference_not_silently_promoted_to_19_05():
    spec, ledger = spec_and_ledger(supported=False)
    result = resolve_recipe(spec, ledger)
    assert result["status"] == "incompatible"
    assert ledger["part_definitions"][0]["finished_mm"]["thickness_mm"] == "18"
    assert not result["operations"]
    assert any("actual_thickness_mm" in message for message in result["findings"])


def test_authored_supported_method_derived_joints_hardware_and_stations():
    spec, ledger = spec_and_ledger()
    result = resolve_recipe(spec, ledger)
    assert result["status"] == "complete"
    assert {j["joint_id"] for j in result["joints"]} == {j["joint_id"] for j in ledger["construction_requirements"]}
    assert len(result["joints"]) == 14
    hardware = {h["hardware_id"]: h for h in result["hardware"]}
    assert hardware["pocket_screw"]["required_quantity"] == 24
    assert hardware["pocket_screw"]["purchased_quantity"] == 100
    assert hardware["back_brad"]["required_quantity"] == 32
    assert hardware["back_brad"]["purchased_quantity"] is None
    pocket = next(j for j in result["joints"] if j["method"] == "pocket_hole_and_glue")
    assert [s["from_front_edge_mm"] for s in pocket["stations"]] == ["22.225", "174.625", "327.025"]
    assert all(s["local_alignment_mm"]["z"] == "9.525" for s in pocket["stations"])
    assert result["physical_review"] == "not_reviewed"
    assert result["review_record"]["physical_record"] is None
    assert result["installation"]["status"] == "site_selection_required"


@pytest.mark.parametrize("mutation,code", [("missing", "JOINT_MISSING"), ("duplicate", "JOINT_DUPLICATE_OR_UNKNOWN"), ("cycle", "OPERATION_CYCLE"), ("part", "PART_UNKNOWN"), ("pair", "JOINT_PAIR_MISMATCH"), ("hardware", "HARDWARE_UNDEFINED"), ("finish", "FINISHING_OPERATION_MISSING"), ("station", "STATION_INVALID"), ("station_world", "STATION_INVALID"), ("count", "HARDWARE_STATION_QUANTITY_MISMATCH"), ("unknown_joint", "JOINT_OPERATION_UNKNOWN")])
def test_recipe_graph_fails_actionably(mutation, code):
    spec, ledger = spec_and_ledger()
    entry = installed_catalog()[(RECIPE_ID, RECIPE_VERSION)]
    graph = build_recipe_graph(entry, spec, ledger)
    if mutation == "missing":
        graph["joints"].pop()
    elif mutation == "duplicate":
        graph["joints"].append(copy.deepcopy(graph["joints"][0]))
    elif mutation == "cycle":
        graph["operations"][0]["depends_on"] = ["final_check"]
    elif mutation == "part":
        graph["operations"][0]["parts"].append("missing_part")
    elif mutation == "pair":
        graph["joints"][0]["instance_ids"] = ["side_left", "side_right"]
    elif mutation == "hardware":
        graph["hardware"][0]["length_mm"] = None
    elif mutation == "station":
        graph["joints"][0]["stations"][0]["local_alignment_mm"]["y"] = "9999"
    elif mutation == "station_world":
        joint = next(j for j in graph["joints"] if j["method"] == "back_glue_and_brad")
        joint["stations"][0]["world_alignment_mm"]["x"] = "9999"
    elif mutation == "count":
        graph["joints"][0]["hardware"][0]["quantity"] = 4
    elif mutation == "unknown_joint":
        graph["operations"][0]["joints"] = ["nonexistent_joint"]
    else:
        graph["operations"] = [o for o in graph["operations"] if o["type"] != "finish_to_size"]
    checked = validate_recipe_graph(graph, ledger, rough_allowance_mm="1" if mutation == "finish" else "0")
    assert not checked["technical_completeness"]
    assert code in {finding["code"] for finding in checked["findings"]}


def test_tools_unavailable_make_instructions_incomplete():
    spec, ledger = spec_and_ledger()
    result = resolve_recipe(spec, ledger, available_tools={"panel_saw"})
    assert result["status"] == "incomplete"
    assert any(f["code"] == "TOOL_UNAVAILABLE" for f in result["validation_findings"])


def test_planned_manufacturing_identity_is_local_and_independent_of_instance_ids():
    spec, ledger = spec_and_ledger()
    result = resolve_recipe(spec, ledger)
    plan = manufacturing_plan(spec, ledger, result)
    assert set(plan) == {i["instance_id"] for i in ledger["part_instances"]}
    assert len(plan["bottom"]) == 6
    assert len(plan["back"]) == 32
    assert plan["bottom"] == plan["shelf_01"] == plan["shelf_02"] == plan["top"]
    assert not plan["side_left"] and not plan["side_right"]
    assert all("instance_id" not in canonical_json(descriptor) and "world_" not in canonical_json(descriptor) for descriptors in plan.values() for descriptor in descriptors)
    assert all(d["geometry_status"] == "reference_only_nominal_cad_blank" for descriptors in plan.values() for d in descriptors)


def test_synthetic_recipe_absent_from_production_catalog():
    assert public_catalog() and all(not r.get("test_only") for r in public_catalog())
    entry = installed_catalog()[(RECIPE_ID, RECIPE_VERSION)]
    entry["test_only"] = True
    entry["recipe_id"] = "synthetic_test_only"
    spec, ledger = spec_and_ledger()
    spec["construction"]["recipe"]["id"] = "synthetic_test_only"
    result = resolve_recipe(spec, ledger, catalog={("synthetic_test_only", RECIPE_VERSION): entry})
    assert result["status"] == "complete"
    assert all(r["recipe_id"] != "synthetic_test_only" for r in public_catalog())
