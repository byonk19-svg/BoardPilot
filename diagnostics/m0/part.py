from decimal import Decimal
from pathlib import Path
import json

from cadgen import build123d as bd
from cadgen import glb, step

HERE = Path(__file__).resolve().parent
KEYS = ("length_mm", "width_mm", "thickness_mm")


@step(out="out/part.step")
@glb(out="out/part.glb")
def part():
    data = json.loads((HERE / "part.json").read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != set(KEYS):
        raise ValueError("Expected exactly the three panel dimensions")
    values = []
    for key in KEYS:
        if not isinstance(data[key], str):
            raise ValueError(f"{key} must be a decimal millimeter string")
        value = Decimal(data[key])
        if not value.is_finite() or value <= 0:
            raise ValueError(f"{key} must be finite and positive")
        values.append(float(value))
    shape = bd.Box(
        *values,
        align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER),
    )
    shape.label = "part"
    return shape


if __name__ == "__main__":
    part()
