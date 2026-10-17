"""Place maintained definitions using the resolved ledger; no woodworking formulas."""
import json
import re
from decimal import Decimal
from pathlib import Path
from woodwork.cad_adapter.windows_runtime import configure_native_platform

configure_native_platform()

from cadgen import build123d as bd
from cadgen import read_step, step

HERE = Path(__file__).resolve().parent
SAFE_ID = re.compile(r"[a-z][a-z0-9_]{0,99}\Z")


@step(out="out/assembly.step")
def assembly():
    data = json.loads((HERE / "assembly.json").read_text(encoding="utf-8"))
    if set(data) != {"part_definitions", "part_instances"}:
        raise ValueError("Invalid assembly driver input")
    definitions = {}
    for definition in data["part_definitions"]:
        definition_id = definition["definition_id"]
        if not SAFE_ID.fullmatch(definition_id) or definition_id in definitions:
            raise ValueError("Invalid definition identity")
        saved = read_step(HERE.parent.parent / "parts" / f"{definition_id}.step")
        if not saved.is_valid or len(saved.solids()) != 1:
            raise ValueError("Maintained definition must contain one valid panel solid")
        # read_step can return a document Compound wrapper with its own child label.
        # Label the physical solid, so XCAF saves one uniquely named leaf occurrence.
        definitions[definition_id] = saved.solids()[0]
    children = []
    seen = set()
    for instance in data["part_instances"]:
        instance_id = instance["instance_id"]
        if not SAFE_ID.fullmatch(instance_id) or instance_id in seen:
            raise ValueError("Invalid instance identity")
        seen.add(instance_id)
        rotation = instance["rotation_cad_rows"]
        center = tuple(float(Decimal(instance["center_mm"][axis])) for axis in "xyz")
        # Plane axes are the columns of the proper local-to-world rotation.
        plane = bd.Plane(origin=center, x_dir=tuple(row[0] for row in rotation), z_dir=tuple(row[2] for row in rotation))
        shape = definitions[instance["definition_id"]].moved(bd.Location(plane))
        shape.label = instance_id
        children.append(shape)
    return bd.Compound(children=children, label="woodworking_assembly")


if __name__ == "__main__":
    assembly()
