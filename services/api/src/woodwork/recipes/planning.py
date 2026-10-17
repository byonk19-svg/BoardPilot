"""Canonical planned manufacturing references; never pretend they are CAD voids."""
from copy import deepcopy

from woodwork.domain import canonical_json


def manufacturing_plan(spec, resolved, recipe):
    """Map stable physical IDs to local descriptors, keeping IDs out of grouping data."""
    plan = {i["instance_id"]: [] for i in resolved["part_instances"]}
    if recipe["status"] != "complete":
        return plan
    hardware = {h["hardware_id"]: h for h in recipe["hardware"]}
    for joint in recipe["joints"]:
        instance_id = joint["machined_instance_id"]
        for station in joint["stations"]:
            if joint["method"] == "pocket_hole_and_glue":
                descriptor = {
                    "operation_type": "planned_jig_drilling", "geometry_status": "reference_only_nominal_cad_blank",
                    "reference_face": station["reference_face"], "reference_edge": station["reference_edge"],
                    "local_alignment_mm": deepcopy(station["local_alignment_mm"]),
                    "tool": "KPHJ720_or_KPHJ720PRO_with_supplied_bit",
                    "tool_setting": {"stop_collar": "3/4_gauged_range", "hole_angle_and_depth": "manufacturer_jig_defined"},
                    "source_ids": sorted(joint["source_ids"]),
                }
            else:
                fastener = hardware["back_brad"]
                descriptor = {
                    "operation_type": "planned_brad_centerline_mark", "geometry_status": "reference_only_nominal_cad_blank",
                    "reference_face": "local_T_positive", "local_alignment_mm": deepcopy(station["local_alignment_mm"]),
                    "fastener": {key: fastener[key] for key in ("type", "sku", "length_mm", "gauge")},
                    "tool": "18g_brad_nailer_1_25in_compatible", "source_ids": sorted(joint["source_ids"]),
                    "layout_basis": "authored_geometric_reference_pending_physical_review",
                }
            plan[instance_id].append(descriptor)
    for instance_id, descriptors in plan.items():
        # Connection enumeration and global positions never change grouping order.
        unique = {canonical_json(d): d for d in descriptors}
        plan[instance_id] = [unique[key] for key in sorted(unique)]
    return plan
