"""The building carbon overview of one OpenBDF project, as the frontend renders it.

GWP in kg CO₂ eq, mass in kg, shares from 0 to 1. Whole life means modules A to C:
module D is reported beside it, never inside it.
"""

from typing import Literal

from pydantic import BaseModel

# What every absolute figure is divided by: nothing, the gross or the useful floor
# area, or the gross floor area and the study period.
Basis = Literal["total", "gfa", "ufa", "gfa_year"]


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
    upfront_share: float  # of the whole life, emitted before the building is used
    per_m2_useful: float | None  # None when the floor area is not declared
    per_m2_gross: float | None
    per_m2_useful_per_year: float | None  # as the COLA sheet
    per_m2_gross_per_year: (
        float | None
    )  # the basis the workbooks declare (1 m2 GFA / year)
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
    share_of_mass: float | None  # of the total mass; None when no mass is declared
    gwp_per_kg: float | None  # None when the mass is zero
    gwp_by_stage: dict[str, float]  # keyed by StageTotal.key


class MassHotspot(BaseModel):
    material: str
    epd_product: str
    mass_kg: float
    share_of_mass: float
    gwp: float  # whole life, so a mass ranking shows its carbon too
    share: float  # of whole-life GWP


class MaterialClassTotal(BaseModel):
    label: str  # OpenBDF material class, "4.2 Concrete"; "Not classified" when blank
    gwp: float
    mass_kg: float


class DataTypeShare(BaseModel):
    key: str
    label: str
    share: float


class ProjectField(BaseModel):
    code: str  # OpenBDF field code in General Information
    label: str
    group: str  # Project | Building | Life cycle assessment
    value: str | None  # as declared; None when General Information leaves it blank


class ModuleCheck(BaseModel):
    module: str  # A1–A3, A1 … C4, in life-cycle order
    declared: bool  # the module's scope flag in General Information
    has_result: bool  # the Wide results hold a non-zero sum for it
    status: str  # ok | declared_no_result | result_not_declared


class BasisOption(BaseModel):
    key: Basis
    label: str
    available: bool
    reason: str | None  # why the building cannot serve it; None when it can


class Units(BaseModel):
    """The basis the figures are on, and the unit each kind of figure reads in."""

    basis: Basis
    carbon: str  # "kg CO₂e per m² GFA"
    mass: str  # divided by area only: mass per year means nothing
    time: str  # the Time section's carbon, by area only: its chart is the years
    intensity: str  # carbon over mass on this basis, "kg CO₂e per kg"


class TimeFigures(BaseModel):
    """The Time section's figures, on the basis's area but never per year."""

    stages: list[StageTotal]
    upfront: float  # A1–A5
    use_per_year: float | None  # B1–B8 spread evenly over the study period
    module_d1: float


class Overview(BaseModel):
    project: ProjectInfo
    project_fields: list[ProjectField]  # the sheet's Project table, in its order
    title_block: list[ProjectField]  # the 14 the Overview heads with, in #97's order
    rows_read: int
    module_checks: list[ModuleCheck]
    modules_declared_without_result: int
    modules_with_undeclared_result: int
    headline: Headline
    stages: list[StageTotal]
    elements: list[ElementTotal]  # the first 8 classified elements, in OpenBDF order
    other_classified: ElementTotal  # classified elements beyond the first 8
    not_classified: ElementTotal  # rows with no element code: shown, never dropped
    element_stages: list[ElementStages]
    material_hotspots: list[MaterialHotspot]  # top 10 by whole-life GWP
    mass_hotspots: list[MassHotspot]  # top 10 by mass
    # Every material, by whole-life GWP: what the top 10s leave out, on request.
    materials: list[MaterialHotspot]
    total_mass_kg: float  # every bill of materials row, floor repetition included
    mass_other_share: float  # of the mass, outside the top 10
    material_classes: list[MaterialClassTotal]  # every class present, in code order
    time: TimeFigures
    units: Units
    bases: list[BasisOption]  # every basis, with whether this building can serve it
    data_type_weighting: str  # gwp_fossil_a1_a3 | mass | not_computed
    data_types: list[DataTypeShare]  # the seven EU 2026/52 types, then "undeclared"
