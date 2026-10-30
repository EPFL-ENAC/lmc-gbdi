"""Buildings as the list, the upload and the comparison show them.

Comparisons are per m² of gross floor area: buildings differ in size, so totals do
not compare. Gross, because the COLA workbooks declare no useful floor area.
"""

from datetime import datetime

from pydantic import BaseModel

from app.overview.schemas import Benchmark


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
    rows_read: int
    whole_life: float
    whole_life_per_m2: float | None  # None when the gross floor area is not declared
    stages_per_m2: dict[str, float] | None  # keyed by StageTotal.key
    leti_band: str | None


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
    benchmarks: list[Benchmark]


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
