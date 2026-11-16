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

__all__ = ["GbdiCounter", "ProjectRecord", "Upload"]

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

    # One number per country and version: the parts of gbdi_id, so no id is stored
    # twice. With the version: a replace stores v2 before it deletes v1.
    __table_args__ = (
        sa.UniqueConstraint(
            "gbdi_country", "gbdi_number", "gbdi_version", name="uq_upload_gbdi_number"
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    project_record_id: int = Field(
        foreign_key="project_record.id", unique=True, ondelete="CASCADE"
    )
    file_name: str
    uploaded_at: datetime = Field(
        sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False)
    )
    # openbdf validation findings kept with the project: warnings, and for a draft
    # the rejects it was stored despite.
    findings: list[dict[str, Any]] = Field(sa_column=sa.Column(JSONB, nullable=False))
    # Stored despite reject findings (`openbdf open --draft`); what they block is in
    # ingest.blocked_parts, read from the findings above.
    draft: bool = Field(
        default=False,
        sa_column=sa.Column(sa.Boolean, nullable=False, server_default=sa.false()),
    )
    # The project id the dashboard gives (app/buildings/gbdi_id.py), and its parts:
    # a replace keeps the country's number and raises the version.
    gbdi_id: str
    gbdi_country: str = Field(max_length=3)
    gbdi_number: int
    gbdi_version: int


class GbdiCounter(SQLModel, table=True):
    """The last number given in each country, `xxx` included. It never goes back, so
    a deleted building leaves a gap and its number is never given again."""

    __tablename__ = "gbdi_counter"

    country: str = Field(primary_key=True, max_length=3)
    last_number: int
