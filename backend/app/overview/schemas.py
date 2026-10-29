"""The building carbon overview of one OpenBDF project, as the frontend renders it.

GWP in kg CO₂ eq, mass in kg, shares from 0 to 1. Whole life means modules A to C:
module D is reported beside it, never inside it.
"""

from pydantic import BaseModel


class ProjectInfo(BaseModel):
    project_id: str | None
    project_name: str | None
    country: str | None
    gross_floor_area_m2: float | None
    useful_floor_area_m2: float | None
    reference_study_period_years: float | None
    lca_database: str | None
    lcia_methodology: str | None
    system_boundary: str | None


class Headline(BaseModel):
    whole_life: float
    upfront: float  # A1–A5
    per_m2_useful: float | None  # None when the floor area is not declared
    per_m2_gross: float | None
    per_m2_useful_per_year: float | None
    module_d1: float
    module_d2: float


class StageTotal(BaseModel):
    key: str
    label: str
    gwp: float
    share: float


class ElementTotal(BaseModel):
    element: str
    gwp: float
    share: float


class ElementStages(BaseModel):
    element: str
    gwp_by_stage: dict[str, float]  # keyed by StageTotal.key
    dominant_stage: str
    dominant_share: float


class MaterialHotspot(BaseModel):
    material: str  # "" when the Bill of Materials row names no material
    epd_product: str
    gwp: float
    mass_kg: float
    share: float  # of whole-life GWP
    gwp_per_kg: float | None  # None when the mass is zero


class MassHotspot(BaseModel):
    material: str
    epd_product: str
    mass_kg: float
    share_of_mass: float


class DataTypeShare(BaseModel):
    key: str
    label: str
    share: float


class Overview(BaseModel):
    project: ProjectInfo
    rows_read: int
    headline: Headline
    stages: list[StageTotal]
    elements: list[ElementTotal]  # the first 8 classified elements, in OpenBDF order
    other_classified: ElementTotal  # classified elements beyond the first 8
    not_classified: ElementTotal  # rows with no element code: shown, never dropped
    element_stages: list[ElementStages]
    material_hotspots: list[MaterialHotspot]  # top 10 by whole-life GWP
    mass_hotspots: list[MassHotspot]  # top 10 by mass
    data_type_weighting: str  # gwp_fossil_a1_a3 | mass | not_computed
    data_types: list[DataTypeShare]  # the seven EU 2026/52 types, then "undeclared"
