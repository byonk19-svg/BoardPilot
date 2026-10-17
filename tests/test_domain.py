"""Supplied arithmetic oracle plus independent world-coordinate checks."""
from fractions import Fraction
import itertools
import json
from pathlib import Path

import jsonschema
import pytest

from woodwork.domain import (
    DomainError, ProjectSpec, canonical_json, compile_project, hash_json,
    normalize_measurement, resolved_hash, resolve_mm,
)

FIXTURES = Path(__file__).parent / "fixtures"
EXPECTED = json.loads((FIXTURES / "bookcase-expected.json").read_text(encoding="utf-8"))
INPUTS = json.loads((FIXTURES / "input-cases.json").read_text(encoding="utf-8"))


def load(name="bookcase-baseline.json"):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def assert_contains(actual, expected):
    if isinstance(expected, dict):
        for key, value in expected.items():
            assert key in actual
            assert_contains(actual[key], value)
    elif isinstance(expected, list):
        assert len(actual) == len(expected)
        for a, e in zip(actual, expected, strict=True):
            assert_contains(a, e)
    else:
        assert actual == expected


@pytest.mark.parametrize("expected", EXPECTED["fixtures"], ids=lambda e: e["input_file"])
def test_complete_supplied_arithmetic_oracle(expected):
    spec = load(expected["input_file"])
    actual = compile_project(spec)
    assert_contains(actual, {k: v for k, v in expected.items() if k != "input_file"})
    assert actual["spec_sha256"] == hash_json(ProjectSpec.model_validate(spec).model_dump(mode="json"))
    assert actual["resolved_sha256"] == resolved_hash(actual)
    assert compile_project(spec) == actual


@pytest.mark.parametrize("expected", EXPECTED["fixtures"], ids=lambda e: e["input_file"])
def test_independent_corner_rotation_volume_and_no_overlap(expected):
    ledger = compile_project(load(expected["input_file"]))
    definitions = {p["definition_id"]: p for p in ledger["part_definitions"]}
    boxes = []
    total = Fraction(0)
    for instance in ledger["part_instances"]:
        part = definitions[instance["definition_id"]]
        dimensions = [Fraction(part["finished_mm"][k]) for k in ("length_mm", "width_mm", "thickness_mm")]
        rotation = instance["rotation_cad_rows"]
        # Dot products and determinant are independent of compiler implementations.
        for i in range(3):
            for j in range(3):
                assert sum(rotation[k][i] * rotation[k][j] for k in range(3)) == int(i == j)
        a, b, c = rotation
        assert a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0]) == 1
        center = [Fraction(instance["center_mm"][axis]) for axis in "xyz"]
        corners = [
            [sum(rotation[row][col] * dimensions[col] * signs[col] / 2 for col in range(3)) + center[row] for row in range(3)]
            for signs in itertools.product((-1, 1), repeat=3)
        ]
        low = [min(corner[axis] for corner in corners) for axis in range(3)]
        high = [max(corner[axis] for corner in corners) for axis in range(3)]
        for i, axis in enumerate("xyz"):
            assert low[i] == Fraction(instance["world_aabb_mm"]["min"][axis])
            assert high[i] == Fraction(instance["world_aabb_mm"]["max"][axis])
        boxes.append((low, high))
        total += dimensions[0] * dimensions[1] * dimensions[2]
        viewer = instance["viewer_center_m"]
        assert [Fraction(viewer[k]) for k in "xyz"] == [center[0]/1000, center[2]/1000, -center[1]/1000]
    assert total == Fraction(ledger["total_part_volume_mm3"])
    for (low_a, high_a), (low_b, high_b) in itertools.combinations(boxes, 2):
        overlaps = [min(high_a[i], high_b[i]) - max(low_a[i], low_b[i]) for i in range(3)]
        assert any(v <= 0 for v in overlaps)
    assert [min(b[0][i] for b in boxes) for i in range(3)] == [Fraction(ledger["world_aabb_mm"]["min"][a]) for a in "xyz"]
    assert [max(b[1][i] for b in boxes) for i in range(3)] == [Fraction(ledger["world_aabb_mm"]["max"][a]) for a in "xyz"]


@pytest.mark.parametrize("case", INPUTS["parse_valid"])
def test_supplied_parser_acceptance(case):
    assert normalize_measurement(case["input"]) == case["expected_mm"]


@pytest.mark.parametrize("text", INPUTS["parse_invalid"] + ["18.0000005 mm", "18.0000015 mm", "30", "1e3 mm", "1/128 in", "1 + 1 in", "0/0 in", "5 ft", "1.5/2 in"])
def test_parser_rejects_invalid_input_without_evaluation_or_rounding(text):
    with pytest.raises(DomainError):
        normalize_measurement(text)


def test_normalization_default_units_and_exact_conversion():
    assert normalize_measurement(' 30 1/2 " ') == "774.7"
    assert normalize_measurement("18.000000", "mm") == "18"
    with pytest.raises(DomainError):
        normalize_measurement("0.0000001 in")
    with pytest.raises(DomainError):
        normalize_measurement("0.00000001 cm")


@pytest.mark.parametrize("case", INPUTS["semantic_invalid"])
def test_supplied_semantic_errors(case):
    spec = load()
    target = spec
    segments = case["path"].split(".")
    for segment in segments[:-1]:
        target = target[segment]
    target[segments[-1]] = case["value"]
    with pytest.raises(DomainError) as error:
        compile_project(spec)
    assert any(f["field"] == case["path"] and f["code"] == case["expected_code"] for f in error.value.findings)


@pytest.mark.parametrize("count", [-1, 1.5, 5, True, "2"])
def test_shelf_count_is_strict_integer(count):
    spec = load()
    spec["dimensions"]["fixed_shelf_count"] = count
    with pytest.raises(DomainError):
        compile_project(spec)


def test_derived_half_even_and_precision_collapse():
    assert resolve_mm(Fraction("18.0000005")) == "18"
    assert resolve_mm(Fraction("18.0000015")) == "18.000002"
    spec = load()
    spec["dimensions"]["outside_height_mm"] = "72.000001"
    with pytest.raises(DomainError) as error:
        compile_project(spec)
    assert "RESOLVED_FEATURE_COLLAPSED" in {e["code"] for e in error.value.findings}


def test_nominal_metadata_does_not_override_measurements():
    baseline = compile_project(load())
    spec = load()
    spec["materials"]["main"]["nominal_label"] = "nominal one inch"
    edited = compile_project(spec)
    assert edited["spec_sha256"] != baseline["spec_sha256"]
    assert edited["geometry_sha256"] == baseline["geometry_sha256"]
    assert edited["part_definitions"] == baseline["part_definitions"]
    spec["materials"]["main"]["actual_thickness_mm"] = "19.05"
    measured = compile_project(spec)
    assert measured["inside_width_mm"] == "723.9"
    assert measured["rounded_clear_height_target_mm"] == "279.4"


def test_allowance_kerf_and_manufacturing_identity_are_distinct():
    baseline = compile_project(load())
    spec = load()
    spec["manufacturing"]["saw_kerf_mm"] = "4"
    kerf = compile_project(spec)
    assert kerf["part_definitions"] == baseline["part_definitions"]
    assert kerf["part_instances"] == baseline["part_instances"]
    assert kerf["geometry_sha256"] == baseline["geometry_sha256"]
    assert kerf["resolved_sha256"] != baseline["resolved_sha256"]
    spec["manufacturing"]["rough_allowance_per_edge_mm"] = "1"
    rough = compile_project(spec)
    assert [p["rough_mm"] for p in rough["part_definitions"]] == [
        {"length_mm":"916.4", "width_mm":"300.8", "thickness_mm":"18"},
        {"length_mm":"728", "width_mm":"300.8", "thickness_mm":"18"},
        {"length_mm":"916.4", "width_mm":"764", "thickness_mm":"6"},
    ]
    assert rough["part_instances"] == baseline["part_instances"]
    assert [p["manufacturing_fingerprint"] for p in rough["part_definitions"]] != [p["manufacturing_fingerprint"] for p in baseline["part_definitions"]]


def test_material_and_stock_foreign_keys_duplicates_and_trim():
    for change in ("material_reference", "duplicate_stock", "duplicate_material", "collapsed_stock"):
        spec = load()
        if change == "material_reference":
            spec["manufacturing"]["stock_sheets"][0]["material_id"] = "missing_material"
        elif change == "duplicate_stock":
            spec["manufacturing"]["stock_sheets"][1]["stock_id"] = "main_sheet"
        elif change == "duplicate_material":
            spec["materials"]["back"]["material_id"] = "plywood_main"
        else:
            spec["manufacturing"]["sheet_edge_trim_mm"] = "610"
        with pytest.raises(DomainError):
            compile_project(spec)
    spec = load()
    spec["manufacturing"]["stock_sheets"] = []
    assert compile_project(spec)["part_instance_count"] == 7
    spec = load()
    spec["manufacturing"]["stock_sheets"][0]["length_mm"] = "900"
    assert compile_project(spec)["part_instance_count"] == 7  # layout is independent of geometry validity


@pytest.mark.parametrize("mutate", [
    lambda s: s.update(schema_version="9.0.0"),
    lambda s: s["template"].update(version="9.0.0"),
    lambda s: s["template"].update(id="not_installed"),
    lambda s: s["dimensions"].update(outside_width_mm="2400.000001"),
    lambda s: s["materials"]["main"].update(actual_thickness_mm="41"),
    lambda s: s["construction"].update(recipe={"id":"not_installed", "version":"1.0.0"}),
    lambda s: s["dimensions"].update(outside_width_mm="18.0000005"),
    lambda s: s["dimensions"].update(outside_width_mm=762),
    lambda s: s.update(untrusted_code="pass"),
])
def test_unsupported_contracts_bounds_and_unknown_fields(mutate):
    spec = load()
    mutate(spec)
    with pytest.raises(DomainError):
        compile_project(spec)


def test_grain_rotation_and_slot_stability():
    slots = []
    for count in (4, 1, 0, 2, 4):
        spec = load()
        spec["dimensions"]["fixed_shelf_count"] = count
        ledger = compile_project(spec)
        ids = [i["instance_id"] for i in ledger["part_instances"]]
        assert [i for i in ids if i.startswith("shelf_")] == [f"shelf_{j:02d}" for j in range(1, count+1)]
        slots.append(ids)
    assert slots[0] == slots[-1]
    spec["materials"]["main"]["face_grain"] = "none"
    ledger = compile_project(spec)
    for part in ledger["part_definitions"][:2]:
        assert part["grain_axis"] == "none"
        assert part["allowed_layout_rotations_deg"] == [0, 90, 180, 270]


def test_generated_schema_is_supplied_contract_compatible_and_deterministic():
    schema = ProjectSpec.model_json_schema()
    supplied = json.loads((FIXTURES / "project.schema.json").read_text(encoding="utf-8"))
    for expected in EXPECTED["fixtures"]:
        spec = load(expected["input_file"])
        jsonschema.Draft202012Validator(schema).validate(spec)
        jsonschema.Draft202012Validator(supplied).validate(ProjectSpec.model_validate(spec).model_dump(mode="json"))
    assert canonical_json({"z": "762", "a": {"b": 2, "a": 1}}) == '{"a":{"a":1,"b":2},"z":"762"}'
    spec = load()
    spec["dimensions"]["outside_width_mm"] = " 0762.000000 "
    assert ProjectSpec.model_validate(spec).dimensions.outside_width_mm == "762"
    assert compile_project(spec)["canonical_spec_sha256"] == EXPECTED["fixtures"][0]["canonical_spec_sha256"]


def test_generated_schema_file_is_current():
    expected = ProjectSpec.model_json_schema()
    expected["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    expected["$id"] = "urn:woodworking-planner:project-spec:1.0.0"
    artifact = Path(__file__).parents[1] / "packages" / "contracts" / "project.schema.json"
    assert json.loads(artifact.read_text(encoding="utf-8")) == expected


def test_installed_default_is_fresh_and_passes_reference_fixture():
    from woodwork.templates import default_project_spec
    first = default_project_spec()
    assert compile_project(first)["spec_sha256"] == EXPECTED["fixtures"][0]["canonical_spec_sha256"]
    first["dimensions"]["outside_width_mm"] = "914.4"
    assert default_project_spec()["dimensions"]["outside_width_mm"] == "762"
