"""Overviews of stored projects, the building list, and two buildings side by side.

Uploads never change once stored, so each overview is computed once per process
and kept under its upload time, read from the database on each request: a building
replaced or deleted by another process is never served from here. Every figure
comes from build_overview, the formulas checked against the workbook: this module
only divides by floor area and aligns.
"""

import asyncio
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.buildings import repo
from app.buildings.ingest import (
    EXAMPLES,
    NO_CARBON_NOTE,
    TOTAL_CHECKS,
    TOTAL_NOTE,
    WHAT_TO_DO,
    WHAT_TO_DO_BY_CODE,
    WORDING,
    blocked_parts,
    parse,
    store,
)
from app.buildings.models import Upload
from app.buildings.schemas import (
    BuildingSummary,
    Comparability,
    CompareCase,
    ComparedBuilding,
    ComparedRow,
    CompareScope,
    Comparison,
    DraftView,
    Finding,
    FindingGroup,
    LeftOut,
    MaterialMass,
    RejectSummary,
)
from app.config import get_settings
from app.db import engine
from app.overview.schemas import Basis, Overview
from app.overview.service import (
    BEC_TIER2,
    STAGES,
    build_overview,
    class_rollup,
    on_basis,
    project_fields,
    project_info,
    scope_stages,
)

# ponytail: per-process cache, each entry with the uploaded_at it was computed from
# and used only while the database still says so. A process that missed a delete
# keeps the entry until restart: bounded by the uploads since boot.
_overviews: dict[int, tuple[datetime, Overview]] = {}
# Drafts whose rejects block carbon have no overview; their summary is kept instead.
_drafts: dict[int, tuple[datetime, BuildingSummary]] = {}
log = logging.getLogger(__name__)


class DraftBlocked(Exception):
    """The draft's rejects block carbon: no overview, comparison or figure."""


def blocked(upload: Upload) -> list[str]:
    return blocked_parts(upload.findings) if upload.draft else []


def rejects(upload: Upload) -> list[str]:
    return [f["message"] for f in upload.findings if f["severity"] == "Reject"]


def findings_count(findings: list[dict]) -> int:
    """Every finding. Older uploads have no count: 1 each."""
    return sum(f.get("count", 1) for f in findings)


SEVERITY_ORDER = {"Reject": 0, "Warning": 1}


def finding_groups(findings: list[dict]) -> list[FindingGroup]:
    """By code, severity and sheet: rejects first, then the most frequent."""
    groups: dict[tuple, FindingGroup] = {}
    for f in findings:
        key = (f["code"], f["severity"], f["sheet"])
        group = groups.setdefault(
            key,
            FindingGroup(
                code=key[0], severity=key[1], sheet=key[2], count=0, examples=[]
            ),
        )
        group.count += f.get("count", 1)
        if len(group.examples) <= EXAMPLES:  # with the entry for the rest, if any
            group.examples.append(Finding(**f))
    return sorted(
        groups.values(), key=lambda g: (SEVERITY_ORDER.get(g.severity, 2), -g.count)
    )


def reject_summary(findings: list[dict]) -> list[RejectSummary]:
    """The rejects by code, across sheets: the count, one message, what to do.

    The condensed entries ("N more ...", count above 1) add to the count only, and
    their messages are not stored. So a code with a condensed entry, or with messages
    that differ, takes the wording of openbdf 0.1.4; a code that has none (a code of
    an older openbdf) shows its first message as an example. The note on the declared
    total goes only to a draft whose carbon is shown; the note on unpaired rows
    only to an E004 that blocks the carbon.
    """
    counts: dict[str, int] = {}
    messages: dict[str, list[str]] = {}
    condensed: set[str] = set()
    for f in findings:
        if f["severity"] != "Reject":
            continue
        code, count = f["code"], f.get("count", 1)
        counts[code] = counts.get(code, 0) + count
        if count > 1:
            condensed.add(code)
        elif f["message"] not in messages.setdefault(code, []):
            messages[code].append(f["message"])
    stands = "carbon" not in blocked_parts(findings)

    def message(code: str) -> str:
        seen = messages.get(code, [])
        if len(seen) == 1 and code not in condensed:
            return seen[0]
        return WORDING.get(code) or (f"For example: {seen[0]}" if seen else code)

    def what_to_do(code: str) -> str:
        text = WHAT_TO_DO_BY_CODE.get(code, WHAT_TO_DO)
        if stands and code in TOTAL_CHECKS:
            text += TOTAL_NOTE
        # Only E004's own findings: the note says that this code blocks the carbon.
        own = [f for f in findings if f["code"] == code]
        if code == "E004" and "carbon" in blocked_parts(own):
            text += NO_CARBON_NOTE
        return text

    return [
        RejectSummary(
            code=code,
            count=counts[code],
            message=message(code),
            what_to_do=what_to_do(code),
        )
        for code in sorted(counts, key=lambda c: (-counts[c], c))
    ]


async def overview(
    session: AsyncSession, project_id: int, basis: Basis = "total"
) -> Overview:
    """The cached overview, its absolute figures divided by the basis."""
    stamp, gbdi_id = await repo.stamp(session, project_id)
    o = on_basis(await overview_of(session, project_id, stamp), basis)
    # After the cache: the backfill sets the id without changing uploaded_at.
    return o.model_copy(update={"gbdi_id": gbdi_id})


async def overview_of(
    session: AsyncSession, project_id: int, stamp: datetime
) -> Overview:
    """The overview of the upload made at `stamp`, from the cache when it has it."""
    hit = _overviews.get(project_id)
    if hit is not None and hit[0] == stamp:
        return hit[1]
    if "carbon" in blocked(await repo.get_upload(session, project_id)):
        raise DraftBlocked(project_id)
    data = await repo.read_project(session, project_id)
    # In a thread: a large project takes seconds, and probes must still answer.
    o = await asyncio.to_thread(build_overview, data)
    _overviews[project_id] = (stamp, o)
    return o


def forget(project_id: int) -> None:
    _overviews.pop(project_id, None)
    _drafts.pop(project_id, None)


def remember(summary: BuildingSummary, o: Overview | None) -> None:
    """Keep what the upload process computed, so nothing is computed twice."""
    if o is not None:
        _overviews[summary.id] = (summary.uploaded_at, o)
    else:
        _drafts[summary.id] = (summary.uploaded_at, summary)


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
        gbdi_id=upload.gbdi_id,
        findings=findings_count(upload.findings),
        project_name=o.project.project_name,
        project_reference=o.project.project_reference,
        project_doi=o.project.project_doi,
        country=o.project.country,
        gross_floor_area_m2=area,
        useful_floor_area_m2=o.project.useful_floor_area_m2,
        study_period_years=o.project.reference_study_period_years,
        rows_read=o.rows_read,
        whole_life=o.headline.whole_life,
        whole_life_per_m2=o.headline.per_m2_gross,
        stages_per_m2={s.key: s.gwp / area for s in o.stages} if area else None,
        scope=o.headline.scope,
        lcia_methodology=o.project.lcia_methodology,
        draft=upload.draft,
        rejects=rejects(upload) if upload.draft else [],
        reject_summary=reject_summary(upload.findings) if upload.draft else [],
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
        gbdi_id=upload.gbdi_id,
        findings=findings_count(upload.findings),
        project_name=project.project_name,
        project_reference=project.project_reference,
        project_doi=project.project_doi,
        country=project.country,
        gross_floor_area_m2=project.gross_floor_area_m2,
        useful_floor_area_m2=project.useful_floor_area_m2,
        study_period_years=project.reference_study_period_years,
        rows_read=rows_read,
        whole_life=None,
        whole_life_per_m2=None,
        stages_per_m2=None,
        lcia_methodology=project.lcia_methodology,
        draft=True,
        blocked=blocked(upload),
        rejects=rejects(upload),
        reject_summary=reject_summary(upload.findings),
    )


async def summary_of(session: AsyncSession, upload: Upload) -> BuildingSummary:
    project_id = upload.project_record_id
    stamp = upload.uploaded_at
    if "carbon" in blocked(upload):
        hit = _drafts.get(project_id)
        if hit is not None and hit[0] == stamp:  # uploads never change: read once
            # but for the id the backfill sets
            return hit[1].model_copy(update={"gbdi_id": upload.gbdi_id})
        data = await repo.read_project(session, project_id, results=False)
        s = draft_summary(upload, data.general, len(data.rows))
        _drafts[project_id] = (stamp, s)
        return s
    return summary(upload, await overview_of(session, project_id, stamp))


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
        findings_count=findings_count(upload.findings),
        finding_groups=finding_groups(upload.findings),
        blocked=parts,
        gross_floor_area_m2=project.gross_floor_area_m2,
        total_mass_kg=None if "materials" in parts else sum(c.mass_kg for c in classes),
        material_classes=[
            MaterialMass(label=c.label, mass_kg=c.mass_kg) for c in classes
        ],
    )


def ingest(
    workbook: bytes, file_name: str, draft: bool, replace: int | None = None
) -> tuple[BuildingSummary, Overview | None]:
    """Read, store and summarise one workbook, in the parser process; with `replace`,
    the project it replaces is deleted in the same transaction.

    Raises RejectedWorkbook, or ValueError when the overview cannot read it: then
    nothing is committed, so a broken project never breaks the list for everyone.
    Returns the overview too (None for a draft without carbon), for the API's cache.
    """
    return asyncio.run(_ingest(workbook, file_name, draft, replace))


async def _ingest(
    workbook: bytes, file_name: str, draft: bool, replace: int | None = None
) -> tuple[BuildingSummary, Overview | None]:
    project, findings = parse(workbook, draft)
    has_rejects = any(f.severity == "Reject" for f in findings)
    # Its own engine: connections never cross processes.
    own = create_async_engine(get_settings().DB_URL)
    try:
        async with AsyncSession(own) as session:
            project_id = await store(
                session, project, file_name, findings, has_rejects, replace
            )
            summary = await building_summary(session, project_id)
            await session.commit()
            hit = _overviews.get(project_id)
            return summary, None if hit is None else hit[1]
    finally:
        await own.dispose()


def compared(upload: Upload, o: Overview) -> ComparedBuilding:
    has_d = o.headline.module_d_present
    return ComparedBuilding(
        id=upload.project_record_id,
        file_name=upload.file_name,
        project_name=o.project.project_name,
        country=o.project.country,
        gross_floor_area_m2=o.project.gross_floor_area_m2,
        rows_read=o.rows_read,
        scope=o.headline.scope,
        lcia_methodology=o.project.lcia_methodology,
        system_boundary=o.project.system_boundary,
        whole_life_per_m2=o.headline.per_m2_gross,
        upfront_per_m2=per_m2(o.headline.upfront, o),
        module_d1_per_m2=per_m2(o.headline.module_d1, o),
        has_module_d=has_d,
        module_d_per_m2=per_m2(o.headline.module_d, o) if has_d else None,
        project_reference=o.project.project_reference,
        project_doi=o.project.project_doi,
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


# The carbon of a row on some stages: the sum of its per-stage carbon, never a
# share of its total. None keeps the total, every stage the building has.
Keys = tuple[str, ...] | None


def on_stages(by_stage: dict[str, float], total: float, keys: Keys) -> float:
    return total if keys is None else sum(by_stage.get(k, 0.0) for k in keys)


def element_totals(o: Overview, keys: Keys = None) -> dict[str, float]:
    return {
        e.element: on_stages(e.gwp_by_stage, e.gwp, keys)
        for e in (*o.elements, o.other_classified, o.not_classified)
    }


UPFRONT = ("a1_a3", "a4_a5")


def compared_on(upload: Upload, o: Overview, keys: Keys) -> ComparedBuilding:
    """compared(), its whole life and upfront figures on `keys` only."""
    c = compared(upload, o)
    if keys is None:
        return c
    gwp = {s.key: s.gwp for s in o.stages}
    return c.model_copy(
        update={
            "whole_life_per_m2": per_m2(sum(gwp[k] for k in keys), o),
            "upfront_per_m2": per_m2(sum(gwp[k] for k in keys if k in UPFRONT), o),
        }
    )


# The field mapping (openbdf_field to standard mapping in v2.0.0) on every gwp_total
# field: "Comparable across methods: No – biogenic scope differs (A1 vs A2)".
METHOD_NOTE = (
    "A2: biogenic INCLUDED in the total (−1/+1 convention). A1: biogenic EXCLUDED "
    "(reported separately, not summed into GWP). Equal for non-biobased; can differ "
    "by the whole biogenic term for biobased. Pool/compare only within the same "
    "lcia_methodology."
)


def comparability(a: str | None, b: str | None) -> Comparability:
    """GWP totals compare one to one only within one LCIA method."""
    if not a or not b:
        return "method_not_declared"
    return "same_method" if a == b else "methods_differ"


LABEL = dict(STAGES)


def compare_case(
    method: Comparability, covered_a: tuple[str, ...], covered_b: tuple[str, ...]
) -> CompareCase:
    if method != "same_method":
        return "methods_differ"
    if not set(covered_a) & set(covered_b):
        return "no_common_stages"
    return "same_stages" if covered_a == covered_b else "different_stages"


def left_out(
    covered_a: tuple[str, ...], covered_b: tuple[str, ...], oa: Overview, ob: Overview
) -> list[LeftOut]:
    gwp = {
        "a": {s.key: s.gwp for s in oa.stages},
        "b": {s.key: s.gwp for s in ob.stages},
    }
    rows = []
    for key, label in STAGES:
        if (key in covered_a) == (key in covered_b):
            continue
        side, o = ("a", oa) if key in covered_a else ("b", ob)
        rows.append(
            LeftOut(
                stage=label,
                not_covered_by="b" if side == "a" else "a",
                value=per_m2(gwp[side][key], o),
            )
        )
    return rows


async def compare(
    session: AsyncSession, a_id: int, b_id: int, scope: CompareScope | None = None
) -> Comparison:
    """Without a scope, the figures each cover their own building's scope, as before
    the parameter existed; "common" sums only the stages both cover."""
    ua, ub = await repo.get_upload(session, a_id), await repo.get_upload(session, b_id)
    oa = await overview_of(session, a_id, ua.uploaded_at)
    ob = await overview_of(session, b_id, ub.uploaded_at)
    method = comparability(oa.project.lcia_methodology, ob.project.lcia_methodology)
    covered_a = scope_stages(oa.module_checks)
    covered_b = scope_stages(ob.module_checks)
    common = tuple(k for k in covered_a if k in covered_b)
    case = compare_case(method, covered_a, covered_b)
    # Without the parameter, every answer keeps the sums of before it existed, each
    # building over its own stages. With it, a merged answer sums the common stages
    # only: on the same stages too, where a result in an undeclared module (a stray
    # B2 under a declared A and C) would else sit inside a figure that names A and C.
    same = case == "same_stages"
    recompute = same or (case == "different_stages" and scope == "common")
    keys = common if scope and recompute else None
    merged = same or keys is not None
    ea, eb = element_totals(oa, keys), element_totals(ob, keys)
    element_order = [name for _, name in BEC_TIER2]
    element_order += ["Other classified elements", "Not classified"]
    ca = {c.label: c for c in oa.material_classes}
    cb = {c.label: c for c in ob.material_classes}
    classes = sorted(ca.keys() | cb.keys())
    a, b = compared_on(ua, oa, keys), compared_on(ub, ob, keys)
    wa, wb = a.whole_life_per_m2, b.whole_life_per_m2

    def labels(stages: tuple[str, ...]) -> list[str]:
        return [LABEL[k] for k in stages]

    return Comparison(
        a=a,
        b=b,
        comparability=method,
        method_note=METHOD_NOTE,
        ratio=wb / wa if wa and wb is not None else None,
        stages=aligned(
            [s.label for s in oa.stages if keys is None or s.key in keys],
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
            {k: on_stages(c.gwp_by_stage, c.gwp, keys) for k, c in ca.items()},
            {k: on_stages(c.gwp_by_stage, c.gwp, keys) for k, c in cb.items()},
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
        case=case,
        applied_scope="common" if merged else "own",
        covered_a=labels(covered_a),
        covered_b=labels(covered_b),
        common_stages=labels(common),
        left_out=left_out(covered_a, covered_b, oa, ob),
        stages_a=labels(common if merged else covered_a),
        stages_b=labels(common if merged else covered_b),
        upfront_stages=labels(tuple(k for k in keys or UPFRONT if k in UPFRONT)),
        # The ratio names its stages only where its two figures were summed on them.
        ratio_stages=labels(common) if merged and (keys is not None) else None,
    )
