"""Bookcase v1 panel equations, using only exact rational arithmetic."""
from fractions import Fraction

TEMPLATE_ID = "plywood_bookcase_v1"
TEMPLATE_VERSION = "1.0.0"
HORIZONTAL = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
SIDE = [[0, 0, -1], [0, 1, 0], [1, 0, 0]]
BACK = [[0, 1, 0], [0, 0, 1], [1, 0, 0]]
CAD_TO_VIEWER = [[1, 0, 0], [0, 0, 1], [0, -1, 0]]


def exact_template(spec):
    dimensions = spec.dimensions
    width = Fraction(dimensions.outside_width_mm)
    height = Fraction(dimensions.outside_height_mm)
    depth = Fraction(dimensions.outside_depth_mm)
    main = Fraction(spec.materials.main.actual_thickness_mm)
    back = Fraction(spec.materials.back.actual_thickness_mm)
    count = dimensions.fixed_shelf_count
    carcass = depth - back
    inside = width - 2 * main
    gap = (height - (count + 2) * main) / (count + 1)
    shelf_ids = [f"shelf_{j:02d}" for j in range(1, count + 1)]
    horizontal_ids = ["bottom", *shelf_ids, "top"]
    definitions = [
        ("panel_side", spec.materials.main, (height, carcass, main), ["side_left", "side_right"]),
        ("panel_horizontal", spec.materials.main, (inside, carcass, main), horizontal_ids),
        ("panel_back", spec.materials.back, (height, width, back), ["back"]),
    ]
    placements = [
        ("side_left", "panel_side", SIDE, (main / 2, carcass / 2, height / 2)),
        ("side_right", "panel_side", SIDE, (width - main / 2, carcass / 2, height / 2)),
        ("bottom", "panel_horizontal", HORIZONTAL, (width / 2, carcass / 2, main / 2)),
    ]
    placements.extend(
        (slot, "panel_horizontal", HORIZONTAL, (width / 2, carcass / 2, j * (gap + main) + main / 2))
        for j, slot in enumerate(shelf_ids, 1)
    )
    placements.extend([
        ("top", "panel_horizontal", HORIZONTAL, (width / 2, carcass / 2, height - main / 2)),
        ("back", "panel_back", BACK, (width / 2, depth - back / 2, height / 2)),
    ])
    return {"width": width, "height": height, "depth": depth, "carcass": carcass, "inside": inside,
            "main": main, "back": back, "gap": gap, "count": count,
            "definitions": definitions, "placements": placements}
