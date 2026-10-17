"""Revision-bound canonical records and formula-safe grouped cut schedules."""
import csv
import hashlib
import json
import uuid
from pathlib import Path

CORE_EXPORT_VERSION = "1.2.0"
CUT_COLUMNS = (
    "revision_id", "spec_sha256", "cut_group_id", "definition_id", "member_instance_ids",
    "description", "material_id", "material_name", "actual_thickness_mm", "quantity",
    "finished_length_mm", "finished_width_mm", "rough_length_mm", "rough_width_mm",
    "grain_axis", "machining_summary", "edge_treatment",
)
CSV_COLUMNS = CUT_COLUMNS + ("definition_ids",)


def canonical_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256_file(path: Path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path: Path, value):
    path.write_bytes(canonical_bytes(value))


def safe_csv_text(value):
    """Quoting is insufficient: neutralize spreadsheet formulas including leading whitespace."""
    text = str(value)
    if text.lstrip(" \t\r\n").startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n")):
        return "'" + text
    return text


def machining_summary(definition):
    planned=definition.get('planned_recipe_operations',[])
    if planned:
        kinds=sorted({p['operation_type'] for p in planned})
        return 'planned '+', '.join(kinds)+'; reference layout; nominal CAD blank'
    return 'none' if not definition.get('machining') else json.dumps(definition['machining'],sort_keys=True)


def write_cut_list(path: Path, spec: dict, resolved: dict, metadata: dict):
    materials = {entry["material_id"]: entry for entry in spec["materials"].values()}
    descriptions = {"panel_side": "Full-height side", "panel_horizontal": "Horizontal panel", "panel_back": "Applied back"}
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for definition in resolved["cut_groups"]:
            finished, rough = definition["finished_mm"], definition["rough_mm"]
            material = materials[definition["material_id"]]
            writer.writerow({
                "revision_id": safe_csv_text(metadata["revision_id"]),
                "spec_sha256": metadata["spec_sha256"],
                "cut_group_id": definition["manufacturing_sha256"],
                "definition_id": safe_csv_text(definition["definition_id"]),
                "member_instance_ids": ";".join(definition["member_instance_ids"]),
                "description": "Interchangeable panel" if len(definition["definition_ids"]) > 1 else descriptions.get(definition["definition_id"], "Panel"),
                "material_id": safe_csv_text(material["material_id"]),
                "material_name": safe_csv_text(material["name"]),
                "actual_thickness_mm": finished["thickness_mm"],
                "quantity": definition["quantity"],
                "finished_length_mm": finished["length_mm"], "finished_width_mm": finished["width_mm"],
                "rough_length_mm": rough["length_mm"], "rough_width_mm": rough["width_mm"],
                "grain_axis": definition["grain_axis"],
                "machining_summary": machining_summary(definition),
                "edge_treatment": safe_csv_text(definition.get("edge_treatment", "none")),
                "definition_ids": ";".join(definition["definition_ids"]),
            })


def artifact_record(root: Path, relative_path: str, kind: str, mime_type: str, metadata: dict, definition_id=None, artifact_id=None):
    path = root / relative_path
    return {
        "artifact_id": artifact_id or str(uuid.uuid4()), "kind": kind, "relative_path": relative_path,
        "mime_type": mime_type, "size_bytes": path.stat().st_size, "sha256": sha256_file(path),
        "revision_id": metadata["revision_id"], "spec_sha256": metadata["spec_sha256"], "definition_id": definition_id,
    }


def write_core_records(out_dir: Path, spec: dict, resolved: dict, metadata: dict):
    write_json(out_dir / "project.json", spec)
    write_json(out_dir / "resolved-project.json", resolved)
    write_cut_list(out_dir / "cut-list.csv", spec, resolved, metadata)
    recipe=resolved.get('construction_recipe',{})
    write_json(out_dir / "materials.json", {"revision_id": metadata["revision_id"], "spec_sha256": metadata["spec_sha256"], "materials": spec["materials"], "hardware": recipe.get('hardware',[]), "hardware_status": resolved['construction_status']})
    (out_dir / "readme.txt").write_text(
        f"Woodworking Planner design geometry set\nRevision: {metadata['revision_id']}\n"
        f"Project ID: {metadata['project_id']}\nTemplate: {spec['template']['id']} {spec['template']['version']}\n"
        "Canonical CAD/CSV units: millimeters. Preview GLB: Y-up meters.\n"
        "One maintained STEP/GLB per manufactured definition; manifest instances place the panels.\n"
        "Import project.json into Woodworking Planner to edit this supported project.\n"
        f"Construction status: {resolved['construction_status']}. Physical review: not recorded.\n"
        "CAD represents finished nominal blanks; planned jig/fastener references are not machined voids.\n"
        "No shelf load rating or public construction approval is implied.\n",
        encoding="utf-8",
    )
