"""Maintained ProjectSpec v1 source; JSON schema is generated from these models."""
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

from .units import MM_PATTERN, canonical_mm

Millimeters = Annotated[str, BeforeValidator(canonical_mm), Field(pattern=MM_PATTERN, max_length=18)]
Identifier = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")]
Version = Annotated[str, Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")]
Name = Annotated[str, Field(min_length=1, max_length=100)]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, str_strip_whitespace=True)


class Template(ContractModel):
    id: Literal["plywood_bookcase_v1"]
    version: Literal["1.0.0"]


class Display(ContractModel):
    preferred_unit: Literal["in", "mm"]
    fraction_denominator: Literal[16, 32, 64]


class Dimensions(ContractModel):
    outside_width_mm: Millimeters
    outside_height_mm: Millimeters
    outside_depth_mm: Millimeters
    fixed_shelf_count: Annotated[int, Field(ge=0, le=4)]


class Material(ContractModel):
    material_id: Identifier
    name: Name
    kind: Literal["plywood"]
    nominal_label: Annotated[str, Field(max_length=80)]
    actual_thickness_mm: Millimeters
    face_grain: Literal["along_L", "none"]


class Materials(ContractModel):
    main: Material
    back: Material


class RecipeSelection(ContractModel):
    id: Identifier
    version: Version


class Construction(ContractModel):
    panel_geometry: Literal["butt_panels"]
    back_style: Literal["applied_full"]
    shelf_spacing: Literal["equal_clear"]
    edge_banding: Literal["none"]
    recipe: RecipeSelection | None


class StockSheet(ContractModel):
    stock_id: Identifier
    material_id: Identifier
    length_mm: Millimeters
    width_mm: Millimeters
    grain_axis: Literal["length", "none"]
    unit_price: Annotated[str, Field(pattern=r"^(?:0|[1-9][0-9]*)\.[0-9]{2}$")] | None
    currency: Literal["USD"]


class Manufacturing(ContractModel):
    saw_kerf_mm: Millimeters
    rough_allowance_per_edge_mm: Millimeters
    sheet_edge_trim_mm: Millimeters
    stock_sheets: Annotated[list[StockSheet], Field(min_length=0, max_length=12)]


class Documents(ContractModel):
    paper_size: Literal["letter", "a4"]
    schedule_units: Literal["dual", "mm"]
    native_part_drawing_units: Literal["mm"]


class ProjectSpec(ContractModel):
    schema_version: Literal["1.0.0"]
    project_name: Name
    template: Template
    display: Display
    dimensions: Dimensions
    materials: Materials
    construction: Construction
    manufacturing: Manufacturing
    documents: Documents
