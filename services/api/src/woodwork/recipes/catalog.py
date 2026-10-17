"""Trusted, versioned fabrication recipes; no provider or import data becomes code."""
from copy import deepcopy
import hashlib
from pathlib import Path

RECIPE_ID = "kreg720_19_05_14in_bookcase"
RECIPE_VERSION = "1.0.0"
AUTHORED = {
    "recipe_id": RECIPE_ID, "version": RECIPE_VERSION,
    "title": "Kreg 720 plywood bookcase - 19.05 mm panels, 6.35 mm back, 14 in depth",
    "method": "KPHJ720/720PRO pocket-hole carcass; separately glued and brad-attached applied back",
    "test_only": False, "technical_completeness": True, "physical_review": "not_recorded",
    "generator_version": "1.0.0", "illustration_contract": "local_station_reference_diagrams_1.0.0",
    "modeling_bounds": {
        "dimensions.outside_width_mm": ["762", "762"], "dimensions.outside_height_mm": ["914.4", "914.4"],
        "dimensions.outside_depth_mm": ["355.6", "355.6"],
        "materials.main.actual_thickness_mm": ["19.05", "19.05"], "materials.back.actual_thickness_mm": ["6.35", "6.35"],
    },
    "applicability": {"template_id": "plywood_bookcase_v1", "main_material_kind": "plywood", "back_material_kind": "plywood", "environment": "indoor", "shelf_count": [0, 4]},
    "required_tools": ["kreg_kphj720_or_720pro", "supplied_easy_set_bit_and_collar", "square_drive_pocket_bit", "drill_driver", "clamps", "panel_saw", "square", "measuring_tools", "18g_brad_nailer_1_25in_compatible"],
    "source_records": [
        {"source_id": "kreg720_manual", "title": "KPHJ720/720PRO Global manual, 06/2020 104909 V1, English pages 12-17", "url": "https://www.kregtool.com/on/demandware.static/-/Library-Sites-RefArchSharedLibrary/default/dw59d64a56/manuals/KPHJ720PRO_Global.pdf", "rule": "Gauge actual stock, select the 3/4 range stop collar and 1-1/4 in screw; clamp joints. Panel guide stations: 5/8 to 1-1/2 in from edges and 6 to 8 in apart."},
        {"source_id": "kreg_screw_guide", "title": "Kreg screw guide, updated June 29, 2026", "url": "https://learn.kregtool.com/learn/how-to-select-right-pocket-hole-screw/", "rule": "Actual thickness governs selection. Coarse thread is preferred for plywood; zinc pocket screws are for indoor dry use."},
        {"source_id": "kreg_bookcase", "title": "Kreg / The Creative Mom Built In Bookcase", "url": "https://learn.kregtool.com/plans/built-in-bookcase/", "rule": "Published method uses 1-1/4 in pocket screws and wood glue, with a separately attached 1/4 in plywood back, wood glue and 1-1/4 in brads. Original dimensions and quantities are not reused."},
        {"source_id": "dewalt_brad", "title": "DEWALT DWBN18PP 18-gauge brad project pack", "url": "https://www.dewalt.com/en-us/product/dwbn18pp/18-gauge-brad-nail-project-pack", "rule": "The indoor steel 18-gauge pack includes 1-1/4 in brads. Select that length; do not mix the other pack lengths into this recipe."},
    ],
    "hardware": [
        {"hardware_id": "pocket_screw", "type": "Kreg #8 coarse-thread zinc Maxi-Loc pocket-hole screw", "sku": "SML-C125-100", "length_mm": "31.75", "length_in": "1.25", "thread": "coarse", "unit": "each", "unit_price": None, "pack_quantity": 100},
        {"hardware_id": "back_brad", "type": "DEWALT indoor steel 18-gauge brad, 1-1/4 in length", "sku": "DWBN18PP - select 1-1/4 in", "length_mm": "31.75", "length_in": "1.25", "gauge": "18", "unit": "each", "unit_price": None, "pack_quantity": None},
    ],
    "consumables": [{"consumable_id": "wood_glue", "description": "Wood glue suitable for indoor plywood; apply and cure per the selected adhesive manufacturer's label", "quantity": None, "unit_price": None}],
    "rules": {"pocket_station_pitch_mm": "152.4", "pocket_station_count_per_end": 3, "back_station_edge_mm": "25.4", "back_station_max_pitch_mm": "180", "finish_to_size": True},
    "author_decisions": [
        "All horizontal panels use the same marked local +T face. The end edge is the jig reference; the manufacturer jig defines hole angle and drilling depth.",
        "Three guide stations per horizontal end are spaced 152.4 mm. At the supported depth, end offsets are 22.225 mm, within the manual's edge range.",
        "Back brads are centered on each contacted carcass edge, with 25.4 mm end offsets and at most 180 mm between stations. This placement is authored, not a manufacturer shelf-load specification.",
        "Hardware identification, edge alignment, joint coverage, dependency order and source consistency received a software technical review. Workholding, driver access, thin-back fastening and service behavior require a physical build review.",
    ],
    "installation": {"status": "site_selection_required", "instruction": "Before putting the bookcase into service, select and review tip-over restraint for the actual wall substrate and intended use. No wall anchor is inferred from geometry.", "source_id": "kreg_bookcase"},
    "review_record": {"technical_scope": "Source, dimensions, local stations, named joint coverage and software dependency checks", "physical_record": None, "load_rating": None},
}


def installed_catalog():
    entry = deepcopy(AUTHORED)
    folder = Path(__file__).parent
    entry["generator_sources"] = {name: hashlib.sha256((folder / name).read_bytes()).hexdigest() for name in ("graph.py", "planning.py")}
    entry["generator_sha256"] = hashlib.sha256(b"".join(name.encode() + b"\0" + (folder / name).read_bytes() for name in ("graph.py", "planning.py"))).hexdigest()
    return {(RECIPE_ID, RECIPE_VERSION): entry}


def public_catalog():
    return [deepcopy(entry) for entry in installed_catalog().values() if not entry.get("test_only")]
