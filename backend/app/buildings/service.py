"""Overviews of stored projects, the building list, and two buildings side by side.

Uploads never change once stored, so each overview is computed once per process
and kept; a delete evicts it. Every figure comes from build_overview, the formulas
checked against the workbook: this module only divides by floor area and aligns.
"""

from sqlmodel.ext.asyncio.session import AsyncSession

from app.buildings import repo
from app.buildings.models import Upload
from app.buildings.schemas import (
    BuildingSummary,
    ComparedBuilding,
    ComparedRow,
    Comparison,
)
from app.overview.schemas import Overview
from app.overview.service import BEC_TIER2, build_overview

# ponytail: per-process cache; ids are never reused, so a replica that missed a
# delete still answers 404 from the database first. Bounded by the projects stored.
_overviews: dict[int, Overview] = {}


async def overview(session: AsyncSession, project_id: int) -> Overview:
    if project_id not in _overviews:
        data = await repo.read_project(session, project_id)
        _overviews[project_id] = build_overview(data)
    return _overviews[project_id]


def forget(project_id: int) -> None:
    _overviews.pop(project_id, None)


def per_m2(value: float, o: Overview) -> float | None:
    area = o.project.gross_floor_area_m2
    return value / area if area else None


def leti_band(o: Overview) -> str | None:
    return next((b.band for b in o.benchmarks if b.key == "leti"), None)


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
        rows_read=o.rows_read,
        whole_life=o.headline.whole_life,
        whole_life_per_m2=o.headline.per_m2_gross,
        stages_per_m2={s.key: s.gwp / area for s in o.stages} if area else None,
        leti_band=leti_band(o),
    )


async def summaries(session: AsyncSession) -> list[BuildingSummary]:
    return [
        summary(upload, await overview(session, upload.project_record_id))
        for upload in await repo.list_uploads(session)
    ]


async def building_summary(session: AsyncSession, project_id: int) -> BuildingSummary:
    upload = await repo.get_upload(session, project_id)
    return summary(upload, await overview(session, project_id))


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
        benchmarks=o.benchmarks,
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
