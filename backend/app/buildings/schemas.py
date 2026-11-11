"""Buildings as the list, the upload and the comparison show them.

Comparisons are per m² of gross floor area: buildings differ in size, so totals do
not compare. Gross, because the COLA workbooks declare no useful floor area.
"""

from datetime import datetime

from pydantic import BaseModel

from app.overview.schemas import ProjectField


class Finding(BaseModel):
    code: str
    severity: str  # Info | Warning | Reject
    sheet: str | None
    row: int | None
    message: str


class BuildingSummary(BaseModel):
    id: int
    file_name: str
    uploaded_at: datetime
    findings: int  # openbdf warnings kept with the upload
    project_name: str | None
    country: str | None
    gross_floor_area_m2: float | None
    useful_floor_area_m2: float | None
    study_period_years: float | None  # the years of use are drawn only with it
    rows_read: int
    # None for a draft whose rejects block carbon: no figure, never a wrong one.
    whole_life: float | None
    whole_life_per_m2: float | None  # None when the gross floor area is not declared
    stages_per_m2: dict[str, float] | None  # keyed by StageTotal.key
    draft: bool = False  # stored despite reject findings
    blocked: list[str] = []  # the parts its rejects block: "carbon", "materials"
    rejects: list[str] = []  # what the rejects say, for the list and the page


class MaterialMass(BaseModel):
    label: str  # OpenBDF material class
    mass_kg: float


class DraftView(BaseModel):
    """What a draft whose rejects block carbon can still show."""

    project_fields: list[ProjectField]
    rows_read: int
    rejects: list[Finding]
    findings: list[Finding]  # everything openbdf reported, warnings included
    blocked: list[str]
    gross_floor_area_m2: float | None
    total_mass_kg: float | None  # None when the rejects block the materials too
    material_classes: list[MaterialMass]


class Rejection(BaseModel):
    message: str
    findings: list[Finding]


class ComparedBuilding(BaseModel):
    id: int
    file_name: str
    project_name: str | None
    country: str | None
    gross_floor_area_m2: float | None
    rows_read: int
    whole_life_per_m2: float | None
    upfront_per_m2: float | None
    module_d1_per_m2: float | None


class ComparedRow(BaseModel):
    label: str
    a: float | None  # per m² of gross floor area; None without a floor area
    b: float | None


class Comparison(BaseModel):
    a: ComparedBuilding
    b: ComparedBuilding
    ratio: float | None  # b's whole life per m² over a's
    stages: list[ComparedRow]  # kg CO₂e per m²
    elements: list[ComparedRow]  # kg CO₂e per m², OpenBDF Tier 2 order
    material_carbon: list[ComparedRow]  # kg CO₂e per m², by OpenBDF material class
    material_mass: list[ComparedRow]  # kg per m², by OpenBDF material class
