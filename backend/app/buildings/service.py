"""Overviews of stored projects, the building list, and two buildings side by side.

Uploads never change once stored, so each overview is computed once per process
and kept; a delete evicts it. Every figure comes from build_overview, the formulas
checked against the workbook: this module only divides by floor area and aligns.
"""

import asyncio
import logging

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.buildings import repo
from app.buildings.ingest import blocked_parts, parse, store
from app.buildings.models import Upload
from app.buildings.schemas import (
    BuildingSummary,
    ComparedBuilding,
    ComparedRow,
    Comparison,
    DraftView,
    MaterialMass,
)
from app.config import get_settings
from app.db import engine
from app.overview.schemas import Basis, Overview
from app.overview.service import (
    BEC_TIER2,
    build_overview,
    class_rollup,
    on_basis,
    project_fields,
    project_info,
)

# ponytail: per-process cache; ids are never reused, so a replica that missed a
# delete still answers 404 from the database first. Bounded by the projects stored.
_overviews: dict[int, Overview] = {}
# Drafts whose rejects block carbon have no overview; their summary is kept instead.
_drafts: dict[int, BuildingSummary] = {}
log = logging.getLogger(__name__)


class DraftBlocked(Exception):
    """The draft's rejects block carbon: no overview, comparison or figure."""


def blocked(upload: Upload) -> list[str]:
    return blocked_parts(upload.findings) if upload.draft else []


def rejects(upload: Upload) -> list[str]:
    return [f["message"] for f in upload.findings if f["severity"] == "Reject"]


async def overview(
    session: AsyncSession, project_id: int, basis: Basis = "total"
) -> Overview:
    """The cached overview, its absolute figures divided by the basis."""
    if project_id not in _overviews:
        if "carbon" in blocked(await repo.get_upload(session, project_id)):
            raise DraftBlocked(project_id)
        data = await repo.read_project(session, project_id)
        # In a thread: a large project takes seconds, and probes must still answer.
        _overviews[project_id] = await asyncio.to_thread(build_overview, data)
    return on_basis(_overviews[project_id], basis)


def forget(project_id: int) -> None:
    _overviews.pop(project_id, None)
    _drafts.pop(project_id, None)


def remember(summary: BuildingSummary, o: Overview | None) -> None:
    """Keep what the upload process computed, so nothing is computed twice."""
    if o is not None:
        _overviews[summary.id] = o
    else:
        _drafts[summary.id] = summary


async def delete(session: AsyncSession, project_id: int) -> None:
    await repo.delete_project(session, project_id)
    await session.commit()
    forget(project_id)


async def warm_up() -> None:
    """Fill the caches after boot, so the list answers from memory. In the background:
    the API answers meanwhile, and a building that cannot be read is logged for its
    own page to report, never fatal for the others."""
    async with AsyncSession(engine) as session:
        for upload in await repo.list_uploads(session):
            try:
                await summary_of(session, upload)
            except Exception:
                log.exception("Building %s could not be read", upload.project_record_id)


def per_m2(value: float, o: Overview) -> float | None:
    area = o.project.gross_floor_area_m2
    return value / area if area else None


def summary(upload: Upload, o: Overview) -> BuildingSummary:
    area = o.project.gross_floor_area_m2
    return BuildingSummary(
        id=upload.project_record_id,
        file_name=upload.file_name,
        uploaded_at=upload.uploaded_at,
        findings=len(upload.findings),
        project_name=o.project.project_name,
        country=o.project.country,
        gross_floor_area_m2=area,
        useful_floor_area_m2=o.project.useful_floor_area_m2,
        study_period_years=o.project.reference_study_period_years,
        rows_read=o.rows_read,
        whole_life=o.headline.whole_life,
        whole_life_per_m2=o.headline.per_m2_gross,
        stages_per_m2={s.key: s.gwp / area for s in o.stages} if area else None,
        draft=upload.draft,
        rejects=rejects(upload) if upload.draft else [],
    )


def draft_summary(
    upload: Upload, general: dict[str, str], rows_read: int = 0
) -> BuildingSummary:
    """A draft whose rejects block carbon: who it is, why it is a draft, no figure."""
    project = project_info(general)
    return BuildingSummary(
        id=upload.project_record_id,
        file_name=upload.file_name,
        uploaded_at=upload.uploaded_at,
        findings=len(upload.findings),
        project_name=project.project_name,
        country=project.country,
        gross_floor_area_m2=project.gross_floor_area_m2,
        useful_floor_area_m2=project.useful_floor_area_m2,
        study_period_years=project.reference_study_period_years,
        rows_read=rows_read,
        whole_life=None,
        whole_life_per_m2=None,
        stages_per_m2=None,
        draft=True,
        blocked=blocked(upload),
        rejects=rejects(upload),
    )


async def summary_of(session: AsyncSession, upload: Upload) -> BuildingSummary:
    project_id = upload.project_record_id
    if "carbon" in blocked(upload):
        if project_id not in _drafts:  # uploads never change: read the lines once
            data = await repo.read_project(session, project_id, results=False)
            _drafts[project_id] = draft_summary(upload, data.general, len(data.rows))
        return _drafts[project_id]
    return summary(upload, await overview(session, project_id))


async def summaries(session: AsyncSession) -> list[BuildingSummary]:
    return [await summary_of(session, u) for u in await repo.list_uploads(session)]


async def building_summary(session: AsyncSession, project_id: int) -> BuildingSummary:
    return await summary_of(session, await repo.get_upload(session, project_id))


async def draft_view(session: AsyncSession, project_id: int) -> DraftView:
    """Project details and, unless blocked too, the materials by mass."""
    upload = await repo.get_upload(session, project_id)
    data = await repo.read_project(session, project_id, results=False)
    parts = blocked(upload)
    classes = [] if "materials" in parts else class_rollup([(r, {}) for r in data.rows])
    project = project_info(data.general)
    return DraftView(
        project_fields=project_fields(data.general),
        rows_read=len(data.rows),
        rejects=[f for f in upload.findings if f["severity"] == "Reject"],
        findings=upload.findings,
        blocked=parts,
        gross_floor_area_m2=project.gross_floor_area_m2,
        total_mass_kg=None if "materials" in parts else sum(c.mass_kg for c in classes),
        material_classes=[
            MaterialMass(label=c.label, mass_kg=c.mass_kg) for c in classes
        ],
    )


def ingest(
    workbook: bytes, file_name: str, draft: bool
) -> tuple[BuildingSummary, Overview | None]:
    """Read, store and summarise one workbook, in the parser process.

    Raises RejectedWorkbook, or ValueError when the overview cannot read it: then
    nothing is committed, so a broken project never breaks the list for everyone.
    Returns the overview too (None for a draft without carbon), for the API's cache.
    """
    return asyncio.run(_ingest(workbook, file_name, draft))


async def _ingest(
    workbook: bytes, file_name: str, draft: bool
) -> tuple[BuildingSummary, Overview | None]:
    project, findings = parse(workbook, draft)
    has_rejects = any(f.severity == "Reject" for f in findings)
    # Its own engine: connections never cross processes.
    own = create_async_engine(get_settings().DB_URL)
    try:
        async with AsyncSession(own) as session:
            project_id = await store(session, project, file_name, findings, has_rejects)
            summary = await building_summary(session, project_id)
            await session.commit()
            return summary, _overviews.get(project_id)
    finally:
        await own.dispose()


def compared(upload: Upload, o: Overview) -> ComparedBuilding:
    return ComparedBuilding(
        id=upload.project_record_id,
        file_name=upload.file_name,
        project_name=o.project.project_name,
        country=o.project.country,
        gross_floor_area_m2=o.project.gross_floor_area_m2,
        rows_read=o.rows_read,
        whole_life_per_m2=o.headline.per_m2_gross,
        upfront_per_m2=per_m2(o.headline.upfront, o),
        module_d1_per_m2=per_m2(o.headline.module_d1, o),
    )


def aligned(
    labels: list[str],
    a: dict[str, float],
    b: dict[str, float],
    oa: Overview,
    ob: Overview,
) -> list[ComparedRow]:
    """One row per label either building has, per m²; absent counts as zero."""
    return [
        ComparedRow(
            label=label,
            a=per_m2(a.get(label, 0.0), oa),
            b=per_m2(b.get(label, 0.0), ob),
        )
        for label in labels
        if label in a or label in b
    ]


def element_totals(o: Overview) -> dict[str, float]:
    return {
        e.element: e.gwp for e in (*o.elements, o.other_classified, o.not_classified)
    }


async def compare(session: AsyncSession, a_id: int, b_id: int) -> Comparison:
    ua, ub = await repo.get_upload(session, a_id), await repo.get_upload(session, b_id)
    oa, ob = await overview(session, a_id), await overview(session, b_id)
    ea, eb = element_totals(oa), element_totals(ob)
    element_order = [name for _, name in BEC_TIER2]
    element_order += ["Other classified elements", "Not classified"]
    ca = {c.label: c for c in oa.material_classes}
    cb = {c.label: c for c in ob.material_classes}
    classes = sorted(ca.keys() | cb.keys())
    wa, wb = oa.headline.per_m2_gross, ob.headline.per_m2_gross
    return Comparison(
        a=compared(ua, oa),
        b=compared(ub, ob),
        ratio=wb / wa if wa and wb is not None else None,
        stages=aligned(
            [s.label for s in oa.stages],
            {s.label: s.gwp for s in oa.stages},
            {s.label: s.gwp for s in ob.stages},
            oa,
            ob,
        ),
        elements=[
            row
            for row in aligned(element_order, ea, eb, oa, ob)
            if (row.a or 0) != 0 or (row.b or 0) != 0
        ],
        material_carbon=aligned(
            classes,
            {k: c.gwp for k, c in ca.items()},
            {k: c.gwp for k, c in cb.items()},
            oa,
            ob,
        ),
        material_mass=aligned(
            classes,
            {k: c.mass_kg for k, c in ca.items()},
            {k: c.mass_kg for k, c in cb.items()},
            oa,
            ob,
        ),
    )
