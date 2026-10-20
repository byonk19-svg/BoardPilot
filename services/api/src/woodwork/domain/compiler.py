"""Single deterministic resolved ledger consumed by geometry and every export."""
from copy import deepcopy
from fractions import Fraction

from pydantic import ValidationError

from woodwork.templates.bookcase import CAD_TO_VIEWER, exact_template

from .errors import DomainError, finding
from .hashing import canonical_json, hash_json, resolved_hash
from .models import ProjectSpec
from .units import exact_decimal, resolve_mm

COMPILER_VERSION = "1.0.0"
MODELING_BOUNDS = {
    "dimensions.outside_width_mm": (100, 2400),
    "dimensions.outside_height_mm": (100, 2400),
    "dimensions.outside_depth_mm": (100, 1000),
    "materials.main.actual_thickness_mm": (6, 40),
    "materials.back.actual_thickness_mm": (1, 20),
}


def validate_spec(value: ProjectSpec | dict) -> ProjectSpec:
    # Revalidation also protects against explicitly unchecked model_construct/copy.
    if isinstance(value, ProjectSpec):
        value = value.model_dump(mode="json")
    try:
        spec = ProjectSpec.model_validate(value)
    except ValidationError as error:
        raise DomainError([
            finding("SCHEMA_INVALID", e["msg"], ".".join(str(s) for s in e["loc"]))
            for e in error.errors(include_url=False, include_input=False)
        ]) from None
    if len(canonical_json(spec).encode("utf-8")) > 256 * 1024:
        raise DomainError([finding("INPUT_TOO_LARGE", "Project exceeds the 256 KiB limit.", "project")])
    return spec


def semantic_findings(spec, exact):
    errors = []
    t, b = exact["main"], exact["back"]
    for role, thickness in (("main", t), ("back", b)):
        if thickness <= 0:
            errors.append(finding("THICKNESS_NOT_POSITIVE", "Measured material thickness must be positive.", f"materials.{role}.actual_thickness_mm"))
    for key, code, field, minimum in (
        ("inside", "INSIDE_WIDTH_NOT_POSITIVE", "dimensions.outside_width_mm", 2*t),
        ("carcass", "CARCASS_DEPTH_NOT_POSITIVE", "dimensions.outside_depth_mm", b),
        ("gap", "CLEAR_OPENING_NOT_POSITIVE", "dimensions.outside_height_mm", (exact["count"]+2)*t),
    ):
        if exact[key] <= 0:
            errors.append(finding(code, "The required clear dimension must be positive.", field, minimum_exclusive_mm=exact_decimal(minimum)))
        elif Fraction(resolve_mm(exact[key])) <= 0:
            errors.append(finding("RESOLVED_FEATURE_COLLAPSED", "A positive feature collapses at 0.000001 mm resolution.", field))
    for path, (minimum, maximum) in MODELING_BOUNDS.items():
        target = spec
        for field in path.split("."):
            target = getattr(target, field)
        if not minimum <= Fraction(target) <= maximum:
            errors.append(finding("MODELING_BOUND_EXCEEDED", "The value is outside this template's supported modeling range.", path, minimum_mm=str(minimum), maximum_mm=str(maximum)))
    material_ids = {spec.materials.main.material_id, spec.materials.back.material_id}
    if len(material_ids) != 2:
        errors.append(finding("MATERIAL_IDS_NOT_DISTINCT", "Main and back require distinct material IDs.", "materials.back.material_id"))
    stocks = set()
    trim = Fraction(spec.manufacturing.sheet_edge_trim_mm)
    for i, stock in enumerate(spec.manufacturing.stock_sheets):
        base = f"manufacturing.stock_sheets.{i}"
        if stock.stock_id in stocks:
            errors.append(finding("STOCK_ID_DUPLICATE", "Stock IDs must be unique.", base + ".stock_id"))
        stocks.add(stock.stock_id)
        if stock.material_id not in material_ids:
            errors.append(finding("MATERIAL_REFERENCE_UNKNOWN", "Stock must reference a declared material.", base + ".material_id"))
        for axis in ("length_mm", "width_mm"):
            if Fraction(getattr(stock, axis)) - 2*trim <= 0:
                errors.append(finding("USABLE_STOCK_NOT_POSITIVE", "Stock dimensions must exceed twice the edge trim.", base + "." + axis, minimum_exclusive_mm=exact_decimal(2*trim)))
    return errors


def vector(values, serializer=resolve_mm):
    return dict(zip("xyz", (serializer(v) for v in values), strict=True))


def multiply(left, right):
    return [[sum(left[i][k] * right[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def transpose(matrix):
    return [list(row) for row in zip(*matrix, strict=True)]


def recipe_state(spec, catalog):
    selection = spec.construction.recipe
    if selection is None:
        return {"status": "recipe_unselected", "fingerprint": None, "findings": [], "technical_completeness": False, "physical_review": "not_recorded"}
    entry = (catalog or {}).get((selection.id, selection.version))
    if entry is None:
        raise DomainError([finding("RECIPE_UNKNOWN", "The selected recipe version is not installed.", "construction.recipe")])
    # Trusted recipe data is supplied by the application, never fetched from input.
    fingerprint = hash_json(entry)
    applicable = True
    findings = []
    for path, bounds in entry.get("modeling_bounds", {}).items():
        target = spec
        for key in path.split("."):
            target = getattr(target, key)
        if not Fraction(str(bounds[0])) <= Fraction(target) <= Fraction(str(bounds[1])):
            applicable = False
            findings.append(finding("RECIPE_INCOMPATIBLE", "Measured parameters are outside the installed recipe's supported range.", path))
    shelf_range=entry.get('applicability',{}).get('shelf_count')
    if shelf_range and not shelf_range[0]<=spec.dimensions.fixed_shelf_count<=shelf_range[1]:
        applicable=False
        findings.append(finding('RECIPE_INCOMPATIBLE','The shelf count is outside this method\'s supported range.','dimensions.fixed_shelf_count'))
    complete = bool(entry.get("technical_completeness", False)) and applicable
    return {"status": "recipe_incompatible" if not applicable else ("recipe_complete" if complete else "recipe_incomplete"),
            "fingerprint": fingerprint, "findings": findings, "technical_completeness": complete,
            "physical_review": entry.get("physical_review", "not_recorded")}


def compile_project(value: ProjectSpec | dict, *, recipe_catalog: dict | None = None) -> dict:
    spec = validate_spec(value)
    exact = exact_template(spec)
    errors = semantic_findings(spec, exact)
    if errors:
        raise DomainError(errors)
    recipe = recipe_state(spec, recipe_catalog)
    allowance = Fraction(spec.manufacturing.rough_allowance_per_edge_mm)
    definitions = []
    definition_dimensions = {}
    material_totals = {}
    total_volume = Fraction(0)
    for definition_id, material, sizes, members in exact["definitions"]:
        length, width, thickness = sizes
        definition_dimensions[definition_id] = sizes
        finished = {k: exact_decimal(v) for k, v in zip(("length_mm", "width_mm", "thickness_mm"), sizes, strict=True)}
        rough = {"length_mm": exact_decimal(length+2*allowance), "width_mm": exact_decimal(width+2*allowance), "thickness_mm": exact_decimal(thickness)}
        grain = "L" if material.face_grain == "along_L" else "none"
        manufacturing_attributes = {"material_id": material.material_id, "material_kind": material.kind,
            "actual_thickness_mm": material.actual_thickness_mm, "finished_mm": finished, "rough_mm": rough,
            "grain_axis": grain, "rough_allowance_per_edge_mm": spec.manufacturing.rough_allowance_per_edge_mm,
            "edge_treatment": spec.construction.edge_banding, "machining": []}
        fingerprint = hash_json(manufacturing_attributes)
        definitions.append({"definition_id": definition_id, "material_id": material.material_id,
            "finished_mm": finished, "rough_mm": rough, "quantity": len(members), "member_instance_ids": members,
            "grain_axis": grain, "allowed_layout_rotations_deg": [0, 180] if grain == "L" else [0, 90, 180, 270],
            "machining": [], "edge_treatment": "none", "manufacturing_attributes": manufacturing_attributes,
            "manufacturing_fingerprint": fingerprint, "manufacturing_sha256": fingerprint})
        totals = material_totals.setdefault(material.material_id, {"material_id": material.material_id,
            "actual_thickness_mm": material.actual_thickness_mm, "part_count": 0, "finished_face_area_mm2": Fraction(0),
            "rough_face_area_mm2": Fraction(0), "volume_mm3": Fraction(0)})
        totals["part_count"] += len(members)
        totals["finished_face_area_mm2"] += length*width*len(members)
        totals["rough_face_area_mm2"] += (length+2*allowance)*(width+2*allowance)*len(members)
        volume = length*width*thickness*len(members)
        totals["volume_mm3"] += volume
        total_volume += volume
    instances = []
    for instance_id, definition_id, rotation, exact_center in exact["placements"]:
        center = tuple(Fraction(resolve_mm(v)) for v in exact_center)
        sizes = definition_dimensions[definition_id]
        extents = [sum(abs(rotation[row][col])*sizes[col]/2 for col in range(3)) for row in range(3)]
        bounds = {"min": vector([center[i]-extents[i] for i in range(3)]), "max": vector([center[i]+extents[i] for i in range(3)])}
        instances.append({"instance_id": instance_id, "definition_id": definition_id,
            "rotation_cad_rows": deepcopy(rotation), "center_mm": vector(center), "world_aabb_mm": bounds,
            "viewer_center_m": vector((center[0]/1000, center[2]/1000, -center[1]/1000), exact_decimal),
            "viewer_rotation_rows": multiply(multiply(CAD_TO_VIEWER, rotation), transpose(CAD_TO_VIEWER))})
    # Measure actual resolved box gaps; do not accumulate an already rounded g.
    horizontals = [i for i in instances if i["definition_id"] == "panel_horizontal"]
    openings = []
    for q, (lower, upper) in enumerate(zip(horizontals[:-1], horizontals[1:], strict=True)):
        low = Fraction(lower["world_aabb_mm"]["max"]["z"])
        high = Fraction(upper["world_aabb_mm"]["min"]["z"])
        openings.append({"opening_index": q, "z_min_mm": exact_decimal(low), "z_max_mm": exact_decimal(high),
            "resolved_clear_height_mm": exact_decimal(high-low), "clear_width_mm": exact_decimal(exact["inside"]),
            "clear_depth_mm": exact_decimal(exact["carcass"])})
    if any(Fraction(o["resolved_clear_height_mm"]) <= 0 for o in openings):
        raise DomainError([finding("RESOLVED_FEATURE_COLLAPSED", "Resolved panel placements leave no positive opening.", "dimensions.outside_height_mm")])
    groups = {}
    for part in definitions:
        group = groups.get(part["manufacturing_sha256"])
        if group is None:
            group = deepcopy(part)
            group["group_id"] = part["manufacturing_sha256"]
            group["definition_ids"] = [part["definition_id"]]
            groups[part["manufacturing_sha256"]] = group
        else:
            group["quantity"] += part["quantity"]
            group["member_instance_ids"].extend(part["member_instance_ids"])
            group["definition_ids"].append(part["definition_id"])
    contact_pairs = [[h["instance_id"], side] for h in horizontals for side in ("side_left", "side_right")]
    contact_pairs.extend([i["instance_id"], "back"] for i in instances if i["instance_id"] != "back")
    spec_dict = spec.model_dump(mode="json")
    spec_hash = hash_json(spec_dict)
    geometry_facts = {"template": spec_dict["template"], "compiler_version": COMPILER_VERSION,
        "definitions": [{"definition_id": p["definition_id"], "finished_mm": p["finished_mm"]} for p in definitions],
        "instances": instances}
    ledger = {"schema_version": "1.0.0", "compiler_version": COMPILER_VERSION, "template": spec_dict["template"],
        "spec": spec_dict, "canonical_spec_sha256": spec_hash, "spec_sha256": spec_hash,
        "geometry_sha256": hash_json(geometry_facts), "part_definition_count": len(definitions), "part_instance_count": len(instances),
        "carcass_depth_mm": exact_decimal(exact["carcass"]), "inside_width_mm": exact_decimal(exact["inside"]),
        "exact_clear_height_mm": {"numerator": str(exact["gap"].numerator), "denominator": str(exact["gap"].denominator)},
        "rounded_clear_height_target_mm": resolve_mm(exact["gap"]), "resolved_position_tolerance_mm": "0.000002",
        "part_definitions": definitions, "part_instances": instances, "cut_groups": list(groups.values()), "openings": openings,
        "world_aabb_mm": {"min": vector((0, 0, 0)), "max": vector((exact["width"], exact["depth"], exact["height"]))},
        "total_part_volume_mm3": exact_decimal(total_volume),
        "material_quantities": [{k: exact_decimal(v) if isinstance(v, Fraction) else v for k, v in row.items()} for row in material_totals.values()],
        "expected_contact_pairs": contact_pairs, "construction_requirements": [{"joint_id": f"attach_{a}_to_{b}", "instance_ids": [a, b]} for a, b in contact_pairs],
        "construction_status": recipe["status"], "construction": recipe, "validation_findings": []}
    ledger["resolved_sha256"] = resolved_hash(ledger)
    return ledger
