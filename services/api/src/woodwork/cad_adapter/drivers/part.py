"""Reviewed parameterless CAD driver. All variable input remains in JSON."""
import json
from decimal import Decimal
from pathlib import Path
from woodwork.cad_adapter.windows_runtime import configure_native_platform

configure_native_platform()

from cadgen import build123d as bd
from cadgen import step

HERE = Path(__file__).resolve().parent
KEYS = ("length_mm", "width_mm", "thickness_mm")


@step(out="out/part.step")
def part():
    data = json.loads((HERE / "part.json").read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != set(KEYS):
        raise ValueError("Expected exactly three resolved panel dimensions")
    values = []
    for key in KEYS:
        if not isinstance(data[key], str):
            raise ValueError("Panel dimensions must be decimal millimeter strings")
        value = Decimal(data[key])
        maximum = Decimal("2400") if key != "thickness_mm" else Decimal("40")
        if not value.is_finite() or not 0 < value <= maximum:
            raise ValueError("Resolved panel dimension outside supported bounds")
        values.append(float(value))
    shape = bd.Box(*values, align=(bd.Align.CENTER,) * 3)
    shape.label = "part"
    return shape


if __name__ == "__main__":
    part()
