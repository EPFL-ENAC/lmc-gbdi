"""Projects in the database, read into the overview's ProjectData.

The overview formulas (app/overview/service.py) were checked against the workbook,
so this module only adapts: OpenBDF records → the same field-code → text mapping
the CSV export gives, and only the columns those formulas read.
"""

from decimal import Decimal
from enum import Enum

from openbdf.model.tables import (
    BuildingBillMaterialsSlimRecord as Line,
)
from openbdf.model.tables import (
    LCAResultsTallFullRecord,
    ProjectMaterialDatabaseRecord,
)
from openbdf.model.tables import (
    LCAResultsWideFullRecord as Wide,
)
from sqlalchemy import delete
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.buildings.models import ProjectRecord, Upload
from app.overview.repo import GWP_FIELDS, MaterialRow, ProjectData


class ProjectNotFound(LookupError):
    pass


def as_text(value: object) -> str:
    """A General Information value as the workbook shows it: enums by their name,
    flags as TRUE/FALSE (what the overview's `declared` reads), blank as ""."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, Enum):
        return str(getattr(value, "display_name", value.value))
    return str(value)


def general_of(record: ProjectRecord) -> dict[str, str]:
    return {name: as_text(getattr(record, name)) for name in ProjectRecord.model_fields}


LINE_COLUMNS = (
    Line.material_id,
    Line.floor_repetition,
    Line.bec_openbdf,
    Line.custom_material_name,
    Line.lca_dataset_material_name,
    Line.material_weight_kg,
    Line.common_material_name,
)


def material_row(values: tuple) -> MaterialRow:
    (material_id, repetition, element, custom, dataset, mass, material_class) = values[
        :7
    ]
    wide_id, *gwp = values[7:]
    if wide_id is None:
        raise ValueError(f"Bill of materials line {material_id!r} has no Wide results")
    return MaterialRow(
        material_id=material_id,
        element=str(element.value) if element else "",
        pair=((custom or "").strip(), (dataset or "").strip()),
        # Blank or 0 counts once, as in the workbook.
        repetition=Decimal(repetition or 1),
        mass_kg=mass or Decimal(0),
        gwp=dict(zip(GWP_FIELDS, gwp, strict=True)),
        material_class=as_text(material_class),
    )


async def read_project(session: AsyncSession, project_id: int) -> ProjectData:
    record = await session.get(ProjectRecord, project_id)
    if record is None:
        raise ProjectNotFound(project_id)
    rows = await session.exec(
        select(*LINE_COLUMNS, Wide.id, *(getattr(Wide, f) for f in GWP_FIELDS))
        .outerjoin(Wide, col(Wide.building_bill_materials_slim_record_id) == Line.id)
        .where(Line.project_id == project_id)
        .order_by(Line.id)
    )
    materials = await session.exec(
        select(
            ProjectMaterialDatabaseRecord.custom_material_name,
            ProjectMaterialDatabaseRecord.lca_dataset_material_name,
            ProjectMaterialDatabaseRecord.material_data_type,
        ).where(ProjectMaterialDatabaseRecord.project_record_id == project_id)
    )
    return ProjectData(
        general=general_of(record),
        rows=[material_row(tuple(r)) for r in rows],
        data_types={
            ((custom or "").strip(), (dataset or "").strip()): as_text(data_type)
            for custom, dataset, data_type in materials
        },
    )


async def list_uploads(session: AsyncSession) -> list[Upload]:
    result = await session.exec(select(Upload).order_by(Upload.file_name))
    return list(result)


async def get_upload(session: AsyncSession, project_id: int) -> Upload:
    upload = (
        await session.exec(select(Upload).where(Upload.project_record_id == project_id))
    ).first()
    if upload is None:
        raise ProjectNotFound(project_id)
    return upload


async def delete_project(session: AsyncSession, project_id: int) -> None:
    """OpenBDF's foreign keys have no ON DELETE: remove children first."""
    await get_upload(session, project_id)
    lines = select(Line.id).where(Line.project_id == project_id)
    for table in (Wide, LCAResultsTallFullRecord):
        await session.exec(
            delete(table).where(
                col(table.building_bill_materials_slim_record_id).in_(lines)
            )
        )
    await session.exec(delete(Line).where(col(Line.project_id) == project_id))
    await session.exec(
        delete(ProjectMaterialDatabaseRecord).where(
            col(ProjectMaterialDatabaseRecord.project_record_id) == project_id
        )
    )
    await session.exec(delete(ProjectRecord).where(col(ProjectRecord.id) == project_id))
