"""Joint-derived hardware and acyclic operation checks, separate from geometry."""
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import math

from woodwork.domain import DomainError, finding, hash_json, resolve_mm
from .catalog import installed_catalog


def _point_rows(start, stop, maximum_pitch):
    span = stop - start
    count = max(1, math.ceil(span / maximum_pitch))
    return [start + span * Fraction(index, count) for index in range(count + 1)]


def build_recipe_graph(entry, spec, resolved):
    definitions = {d["definition_id"]: d for d in resolved["part_definitions"]}
    instances = {i["instance_id"]: i for i in resolved["part_instances"]}
    joints = []
    rules = entry["rules"]
    pitch = Fraction(rules["pocket_station_pitch_mm"])
    edge = Fraction(rules["back_station_edge_mm"])
    back_pitch = Fraction(rules["back_station_max_pitch_mm"])
    height = Fraction(spec["dimensions"]["outside_height_mm"])
    width = Fraction(spec["dimensions"]["outside_width_mm"])
    back_t = Fraction(spec["materials"]["back"]["actual_thickness_mm"])
    for required in resolved["construction_requirements"]:
        members = required["instance_ids"]
        if "back" not in members:
            panel = next(i for i in members if i in {"bottom", "top"} or i.startswith("shelf_"))
            side = next(i for i in members if i.startswith("side_"))
            definition = definitions[instances[panel]["definition_id"]]
            length = Fraction(definition["finished_mm"]["length_mm"])
            local_x = -length / 2 if side == "side_left" else length / 2
            stations = [{"reference_face": "local_T_positive", "reference_edge": "local_L_negative" if side == "side_left" else "local_L_positive", "local_alignment_mm": {"x": resolve_mm(local_x), "y": resolve_mm(y), "z": resolve_mm(Fraction(definition["finished_mm"]["thickness_mm"]) / 2)}, "from_front_edge_mm": resolve_mm(Fraction(definition["finished_mm"]["width_mm"]) / 2 + y), "geometry": "jig_reference_station_not_hole_outline"} for y in (-pitch, Fraction(0), pitch)]
            joints.append({**deepcopy(required), "method": "pocket_hole_and_glue", "machined_instance_id": panel, "stations": stations, "hardware": [{"hardware_id": "pocket_screw", "quantity": len(stations)}], "source_ids": ["kreg720_manual", "kreg_screw_guide"]})
        else:
            part = next(i for i in members if i != "back")
            instance = instances[part]
            definition = definitions[instance["definition_id"]]
            if part.startswith("side_"):
                x = Fraction(instance["center_mm"]["x"])
                positions = [(x, z) for z in _point_rows(edge, height - edge, back_pitch)]
            else:
                length = Fraction(definition["finished_mm"]["length_mm"])
                x0 = Fraction(instance["center_mm"]["x"]) - length / 2
                positions = [(x, Fraction(instance["center_mm"]["z"])) for x in _point_rows(x0 + edge, x0 + length - edge, back_pitch)]
            stations = [{"reference_face": "back_local_T_positive", "local_alignment_mm": {"x": resolve_mm(z - height / 2), "y": resolve_mm(x - width / 2), "z": resolve_mm(back_t / 2)}, "world_alignment_mm": {"x": resolve_mm(x), "y": spec["dimensions"]["outside_depth_mm"], "z": resolve_mm(z)}} for x, z in positions]
            joints.append({**deepcopy(required), "method": "back_glue_and_brad", "machined_instance_id": "back", "stations": stations, "hardware": [{"hardware_id": "back_brad", "quantity": len(stations)}], "source_ids": ["kreg_bookcase", "dewalt_brad"], "decision_basis": "authored_geometric_layout_pending_physical_review"})
    all_parts = list(instances)
    operations = [{"operation_id": "cut_and_label", "type": "cut", "parts": all_parts, "depends_on": [], "joints": [], "tools": ["panel_saw", "measuring_tools"], "instruction": "Cut and label every rough blank from this revision's cut schedule. Preserve grain along local L."}]
    preparation = "cut_and_label"
    if rules.get("finish_to_size"):
        operations.append({"operation_id": "finish_to_size", "type": "finish_to_size", "parts": all_parts, "depends_on": [preparation], "joints": [], "tools": ["panel_saw", "measuring_tools"], "instruction": "Finish each rough blank to its exact finished L and W in the part schedule. Check actual thickness; rough allowance does not increase thickness."})
        preparation = "finish_to_size"
    operations.append({"operation_id": "set_jig", "type": "setup", "parts": all_parts, "depends_on": [preparation], "joints": [], "tools": ["kreg_kphj720_or_720pro", "supplied_easy_set_bit_and_collar"], "instruction": "Check the measured main stock against the Kreg gauge's 3/4 range, set the supplied stop collar to that range, and securely clamp each panel. Use the manufacturer's jig procedure; no drill angle or depth is inferred from CAD."})
    horizontal = [i for i in all_parts if i in {"bottom", "top"} or i.startswith("shelf_")]
    for panel in horizontal:
        operations.append({"operation_id": f"drill_{panel}", "type": "drill", "parts": [panel], "depends_on": ["set_jig"], "joints": [], "tools": ["kreg_kphj720_or_720pro", "drill_driver"], "instruction": f"Mark {panel}'s local +T face. Align each end with the jig at the three listed stations measured from its front edge; drill the six pockets while the panel is still loose."})
    operations.append({"operation_id": "dry_fit", "type": "inspect", "parts": all_parts, "depends_on": [f"drill_{p}" for p in horizontal], "joints": [], "tools": ["square", "clamps"], "instruction": "Dry fit the carcass on a supported work surface. Compare each labeled panel center and each clear opening to this revision's drawing; check squareness before adhesive."})
    left_ids = [j["joint_id"] for j in joints if j["method"] == "pocket_hole_and_glue" and "side_left" in j["instance_ids"]]
    right_ids = [j["joint_id"] for j in joints if j["method"] == "pocket_hole_and_glue" and "side_right" in j["instance_ids"]]
    operations.extend([
        {"operation_id": "attach_left", "type": "fasten", "parts": ["side_left", *horizontal], "depends_on": ["dry_fit"], "joints": left_ids, "tools": ["clamps", "square_drive_pocket_bit", "drill_driver"], "instruction": "Lay side_left on a supported work surface. Apply the selected glue per its label, clamp each horizontal panel in its drawn position, and seat the three specified pocket screws at each left end without overdriving."},
        {"operation_id": "attach_right", "type": "fasten", "parts": ["side_right", *horizontal], "depends_on": ["attach_left"], "joints": right_ids, "tools": ["clamps", "square_drive_pocket_bit", "drill_driver"], "instruction": "Fit side_right to the horizontal ends, keep the carcass square, clamp the joints and seat three specified screws per right end. Keep the front open for driver access."},
        {"operation_id": "attach_back", "type": "fasten", "parts": all_parts, "depends_on": ["attach_right"], "joints": [j["joint_id"] for j in joints if j["method"] == "back_glue_and_brad"], "tools": ["clamps", "18g_brad_nailer_1_25in_compatible", "square"], "instruction": "Support the square carcass face-down. Transfer the listed carcass-edge centerlines to back, apply wood glue per its label, clamp the back flush, and drive only the specified 1-1/4 in brads on those lines. Check the thin back and all edges for unintended breakout."},
        {"operation_id": "final_check", "type": "inspect", "parts": all_parts, "depends_on": ["attach_back"], "joints": [], "tools": ["square", "measuring_tools"], "instruction": "Allow adhesive to cure per its label. Check squareness, finished dimensions, clear openings, seated fasteners and breakout. Before use, arrange site-specific tip-over restraint and record the physical review; no shelf load rating is supplied."},
    ])
    return {"joints": joints, "operations": operations, "hardware": deepcopy(entry["hardware"])}


def validate_recipe_graph(graph, resolved, *, required_tools=(), available_tools=None, rough_allowance_mm="0"):
    findings = []
    parts = {i["instance_id"] for i in resolved["part_instances"]}
    required = {j["joint_id"] for j in resolved["construction_requirements"]}
    expected_pairs = {j["joint_id"]: set(j["instance_ids"]) for j in resolved["construction_requirements"]}
    counts = Counter(j["joint_id"] for j in graph.get("joints", []))
    for joint_id in sorted(required - set(counts)):
        findings.append({"code": "JOINT_MISSING", "message": f"Missing required connection {joint_id}", "joint_id": joint_id})
    for joint_id, count in counts.items():
        if count != 1 or joint_id not in required:
            findings.append({"code": "JOINT_DUPLICATE_OR_UNKNOWN", "message": f"Connection {joint_id} does not resolve exactly once", "joint_id": joint_id})
    hardware = {h["hardware_id"]: h for h in graph.get("hardware", [])}
    definitions = {d["definition_id"]: d for d in resolved["part_definitions"]}
    instances = {i["instance_id"]: i for i in resolved["part_instances"]}
    totals = Counter()
    for joint in graph.get("joints", []):
        if not set(joint.get("instance_ids", [])) <= parts or len(joint.get("instance_ids", [])) != 2:
            findings.append({"code": "PART_UNKNOWN", "message": f"Connection {joint['joint_id']} references missing parts"})
        if joint["joint_id"] in expected_pairs and set(joint.get("instance_ids", [])) != expected_pairs[joint["joint_id"]]:
            findings.append({"code": "JOINT_PAIR_MISMATCH", "message": f"Connection {joint['joint_id']} names the wrong panel pair"})
        if not joint.get("stations"):
            findings.append({"code": "STATIONS_MISSING", "message": f"Connection {joint['joint_id']} has no fastening stations"})
        machined = instances.get(joint.get("machined_instance_id"))
        if machined is None:
            findings.append({"code": "PART_UNKNOWN", "message": f"Connection {joint['joint_id']} has no valid machining-reference part"})
        else:
            dims = definitions[machined["definition_id"]]["finished_mm"]
            half = [Fraction(dims[key]) / 2 for key in ("length_mm", "width_mm", "thickness_mm")]
            for station in joint.get("stations", []):
                try:
                    point = [Fraction(station["local_alignment_mm"][axis]) for axis in "xyz"]
                    valid = all(abs(point[i]) <= half[i] for i in range(3)) and point[2] == half[2]
                    valid = valid and station.get("reference_face") in {"local_T_positive", "back_local_T_positive"}
                    if "world_alignment_mm" in station:
                        world = [sum(Fraction(machined["rotation_cad_rows"][i][j]) * point[j] for j in range(3)) + Fraction(machined["center_mm"][axis]) for i, axis in enumerate("xyz")]
                        valid = valid and all(abs(world[i] - Fraction(station["world_alignment_mm"][axis])) <= Fraction("0.000002") for i, axis in enumerate("xyz"))
                except (ValueError, TypeError, ZeroDivisionError, KeyError):
                    valid = False
                if not valid:
                    findings.append({"code": "STATION_INVALID", "message": f"Connection {joint['joint_id']} has a station outside its local face or inconsistent world transform"})
        if sum(use.get("quantity", 0) for use in joint.get("hardware", []) if type(use.get("quantity")) is int) != len(joint.get("stations", [])):
            findings.append({"code": "HARDWARE_STATION_QUANTITY_MISMATCH", "message": f"Connection {joint['joint_id']} must derive fastener count from its stations"})
        for use in joint.get("hardware", []):
            record = hardware.get(use["hardware_id"])
            try:
                sized = record is not None and Fraction(record.get("length_mm", "0")) > 0
            except (ValueError, TypeError, ZeroDivisionError):
                sized = False
            if not sized or not record.get("type") or not record.get("sku") or not (record.get("gauge") or record.get("thread")):
                findings.append({"code": "HARDWARE_UNDEFINED", "message": f"Hardware {use['hardware_id']} needs a defined type, dimensions and installation identity"})
            if type(use.get("quantity")) is not int or use["quantity"] <= 0:
                findings.append({"code": "HARDWARE_QUANTITY_INVALID", "message": "Fastener quantity must be a positive integer"})
            else:
                totals[use["hardware_id"]] += use["quantity"]
    operations = graph.get("operations", [])
    ids = [o["operation_id"] for o in operations]
    if len(set(ids)) != len(ids):
        findings.append({"code": "OPERATION_DUPLICATE", "message": "Operation IDs must be unique"})
    unresolved = {o["operation_id"]: set(o.get("depends_on", [])) for o in operations}
    ordered = []
    joint_operations = Counter()
    for op in operations:
        if not set(op.get("parts", [])) <= parts:
            findings.append({"code": "PART_UNKNOWN", "message": f"Operation {op['operation_id']} references a missing part"})
        if not set(op.get("depends_on", [])) <= set(ids):
            findings.append({"code": "DEPENDENCY_UNKNOWN", "message": f"Operation {op['operation_id']} references a missing dependency"})
        if not op.get("instruction"):
            findings.append({"code": "INSTRUCTION_MISSING", "message": f"Operation {op['operation_id']} has no instructions"})
        if not set(op.get("joints", [])) <= required:
            findings.append({"code": "JOINT_OPERATION_UNKNOWN", "message": f"Operation {op['operation_id']} references an unknown connection"})
        joint_operations.update(op.get("joints", []))
    for joint_id in sorted(required):
        if joint_operations[joint_id] != 1:
            findings.append({"code": "JOINT_OPERATION_MISSING_OR_DUPLICATE", "message": f"Connection {joint_id} must be attached by exactly one operation"})
    while unresolved:
        ready = sorted(key for key, dependencies in unresolved.items() if not dependencies)
        if not ready:
            findings.append({"code": "OPERATION_CYCLE", "message": "Operation dependencies contain a cycle or unresolved reference"})
            break
        for key in ready:
            ordered.append(key)
            unresolved.pop(key)
        for dependencies in unresolved.values():
            dependencies.difference_update(ready)
    if available_tools is not None:
        for tool in sorted((set(required_tools) | {tool for op in operations for tool in op.get("tools", [])}) - set(available_tools)):
            findings.append({"code": "TOOL_UNAVAILABLE", "message": f"Required tool unavailable: {tool}", "tool": tool})
    if Fraction(rough_allowance_mm) > 0 and not any(o.get("type") == "finish_to_size" for o in operations):
        findings.append({"code": "FINISHING_OPERATION_MISSING", "message": "Rough allowance requires a finishing-to-size operation"})
    quantities = []
    for hardware_id, record in hardware.items():
        pack = record.get("pack_quantity")
        pack_count = math.ceil(totals[hardware_id] / pack) if type(pack) is int and pack > 0 else None
        quantities.append({**record, "required_quantity": totals[hardware_id], "packs_purchased": pack_count,
                           "purchased_quantity": pack_count * pack if pack_count is not None else None})
    return {"technical_completeness": not findings, "findings": findings, "ordered_operation_ids": ordered, "hardware": quantities}


def resolve_recipe(spec, resolved, *, catalog=None, available_tools=None):
    selection = spec["construction"]["recipe"]
    if selection is None:
        return {"status": "recipe_unselected", "recipe_id": None, "recipe_version": None, "fingerprint": None, "physical_review": "not_reviewed", "technical_completeness": False, "findings": ["Choose a compatible construction method; this revision is a design packet."], "joints": [], "operations": [], "hardware": []}
    entry = (installed_catalog() if catalog is None else catalog).get((selection["id"], selection["version"]))
    if entry is None or entry.get("test_only") and catalog is None:
        raise DomainError([finding("RECIPE_UNKNOWN", "The selected recipe version is not installed.", "construction.recipe")])
    incompatibilities = []
    for path, limits in entry.get("modeling_bounds", {}).items():
        value = spec
        for key in path.split("."):
            value = value[key]
        if not Fraction(limits[0]) <= Fraction(value) <= Fraction(limits[1]):
            incompatibilities.append(f"{path}: supported measured range {limits[0]} to {limits[1]} mm; received {value} mm")
    if spec["template"]["id"] != entry["applicability"]["template_id"]:
        incompatibilities.append("Unsupported template for this construction method")
    graph = build_recipe_graph(entry, spec, resolved) if not incompatibilities else {"joints": [], "operations": [], "hardware": []}
    checked = validate_recipe_graph(graph, resolved, required_tools=entry["required_tools"], available_tools=available_tools, rough_allowance_mm=spec["manufacturing"]["rough_allowance_per_edge_mm"]) if not incompatibilities else {"technical_completeness": False, "findings": [], "ordered_operation_ids": [], "hardware": []}
    operations = {o["operation_id"]: o for o in graph["operations"]}
    return {"status": "incompatible" if incompatibilities else ("complete" if checked["technical_completeness"] else "incomplete"), "recipe_id": selection["id"], "recipe_version": selection["version"], "fingerprint": hash_json(entry), "physical_review": "not_reviewed", "technical_completeness": checked["technical_completeness"], "findings": incompatibilities + [f["message"] for f in checked["findings"]], "validation_findings": checked["findings"], "joints": graph["joints"], "operations": [operations[i] for i in checked["ordered_operation_ids"]], "hardware": checked["hardware"], "required_tools": entry["required_tools"], "source_records": entry["source_records"], "author_decisions": entry["author_decisions"], "installation": entry["installation"], "review_record": entry["review_record"], "consumables": entry["consumables"]}
