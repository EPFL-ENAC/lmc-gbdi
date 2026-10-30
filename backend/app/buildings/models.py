"""The database: OpenBDF's own tables (lmc-openbdf), plus one row per uploaded workbook.

The OpenBDF schema is imported, never copied: a new lmc-openbdf revision brings its
columns with it, and `alembic revision --autogenerate` picks them up.
"""

from datetime import datetime
from typing import Any

import sqlalchemy as sa
from openbdf.model.tables import (
    BuildingBillMaterialsSlimRecord,
    LCAResultsTallFullRecord,
    LCAResultsWideFullRecord,
    ProjectMaterialDatabaseRecord,
    ProjectRecord,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

__all__ = ["ProjectRecord", "Upload"]

# OpenBDF's foreign keys carry no index: reading one project, or deleting it (each
# line checks the result tables that point at it), would scan whole tables.
for name, column in (
    ("ix_bom_project", BuildingBillMaterialsSlimRecord.__table__.c.project_id),
    ("ix_pmd_project", ProjectMaterialDatabaseRecord.__table__.c.project_record_id),
    (
        "ix_wide_line",
        LCAResultsWideFullRecord.__table__.c.building_bill_materials_slim_record_id,
    ),
    (
        "ix_tall_line",
        LCAResultsTallFullRecord.__table__.c.building_bill_materials_slim_record_id,
    ),
):
    sa.Index(name, column)


class Upload(SQLModel, table=True):
    """Where a project came from: the workbook, when, and what openbdf found in it."""

    id: int | None = Field(default=None, primary_key=True)
    project_record_id: int = Field(
        foreign_key="project_record.id", unique=True, ondelete="CASCADE"
    )
    file_name: str
    uploaded_at: datetime = Field(
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False)
    )
    # openbdf validation findings kept with the project: warnings only, rejects
    # never reach the database.
    findings: list[dict[str, Any]] = Field(sa_column=sa.Column(JSONB, nullable=False))
