"""Workbook → OpenBDF records → database, through lmc-openbdf's own parser.

The same path for the upload endpoint and scripts/load_buildings.py. Parsing a COLA
workbook takes 15–60 s of CPU, so the endpoint runs `parse` in a worker thread.
"""

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from openbdf.lib.converters.dataframe import project_package_from_tables
from openbdf.lib.converters.translators import DocumentTranslator
from openbdf.lib.openbdf_tables import OpenBDFTables
from openbdf.lib.sources import ExcelSheetSource
from openbdf.lib.validation import (
    DroppedLine,
    OpenBDFValidationError,
    Severity,
    sort_findings,
    validate_project,
)
from sqlmodel.ext.asyncio.session import AsyncSession

from app.buildings import repo
from app.buildings.models import ProjectRecord, Upload


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str  # Info | Warning | Reject
    sheet: str | None
    row: int | None
    message: str
    count: int = 1  # above 1, the entry stands for the rest of its code and sheet


# The first findings of each code and sheet are kept, the rest become one entry with a
# count: AT-09 alone reports about 190 000, too many for one JSONB cell or a 422 body.
EXAMPLES = 20


def condense(findings: list[Finding]) -> list[Finding]:
    totals = Counter((f.code, f.sheet) for f in findings)
    seen: Counter[tuple[str, str | None]] = Counter()
    kept = []
    for f in findings:
        key = (f.code, f.sheet)
        seen[key] += 1
        rest = totals[key] - EXAMPLES
        if seen[key] <= EXAMPLES or rest == 1:
            kept.append(f)
        elif seen[key] == EXAMPLES + 1:
            message = f"{rest} more {f.code} findings on this sheet"
            kept.append(Finding(f.code, f.severity, f.sheet, None, message, rest))
    return kept


class RejectedWorkbook(Exception):
    """Reject findings: nothing is stored, as `openbdf open` saves nothing."""

    def __init__(self, findings: list[Finding]):
        super().__init__(f"{len(findings)} findings, some of them rejects")
        self.findings = findings


# What a reject leaves unreadable, by the sheet it names. A draft keeps every other
# part: General Information rejects (a missing country) block nothing.
RESULT_SHEETS = ("LCA Result (Wide)", "LCA Result (Tall)")
PROJECT_SHEETS = ("General Information", "Project Material Database")


def blocked_parts(findings: list[dict]) -> list[str]:
    """The parts of a stored draft that cannot be shown: "carbon", "materials".

    Results paired to the wrong lines (E05) block carbon. A reject on the bill of
    materials, or one naming no sheet, blocks both, as nothing proves the lines.
    """
    blocked: set[str] = set()
    for f in findings:
        if f["severity"] != "Reject" or f["sheet"] in PROJECT_SHEETS:
            continue
        blocked.add("carbon")
        if f["sheet"] not in RESULT_SHEETS:
            blocked.add("materials")
    return sorted(blocked)


def finding(f: OpenBDFValidationError) -> Finding:
    return Finding(f.code, f.severity.value, f.source, f.row, f.message)


def parse(workbook: bytes, draft: bool = False) -> tuple[ProjectRecord, list[Finding]]:
    """The lmc-openbdf README's ingest: translate, convert, validate.

    A draft is stored despite its rejects, as `openbdf open --draft` saves; the parts
    they block are emptied first, so no misaligned figure is ever stored.
    """
    translator = DocumentTranslator.default_openbdf_translator()
    findings: list[OpenBDFValidationError] = []
    with ExcelSheetSource([workbook]) as source:
        tables = OpenBDFTables.from_source(source, translator)
    if tables is None:
        raise RejectedWorkbook(
            [
                Finding(
                    "E00",
                    "Reject",
                    None,
                    None,
                    "No General Information or Bill of Materials sheet.",
                )
            ]
        )
    project = project_package_from_tables(
        tables, translator, findings=findings, draft=draft
    )
    dropped = frozenset(
        f.row for f in findings if isinstance(f, DroppedLine) and f.row is not None
    )
    findings += validate_project(
        project, tables, document_translator=translator, dropped_rows=dropped
    )
    found = condense([finding(f) for f in sort_findings(findings)])
    if not draft and any(f.severity == Severity.REJECT.value for f in found):
        raise RejectedWorkbook(found)
    if "carbon" in blocked_parts([f.__dict__ for f in found]):
        # Draft mode pairs results to lines by position: wrong pairs look real.
        for line in project.bill_of_materials:
            line.lca_results_full_record = None
    # ponytail: the tall results are the wide ones unpivoted (16 rows per line,
    # 230k for OASE) and nothing reads them; store them when something does.
    for line in project.bill_of_materials:
        line.lca_results_tall_full_records = []
    return project, found


async def store(
    session: AsyncSession,
    project: ProjectRecord,
    file_name: str,
    findings: list[Finding],
    draft: bool = False,
    replace: int | None = None,
) -> int:
    """Add the project graph and its upload row, and delete the project it replaces;
    the caller commits, so a failed upload keeps the old one."""
    session.add(project)
    await session.flush()
    assert project.id is not None
    session.add(
        Upload(
            project_record_id=project.id,
            file_name=Path(file_name).name,
            uploaded_at=datetime.now(UTC),
            findings=[f.__dict__ for f in findings],
            draft=draft,
        )
    )
    await session.flush()
    if replace is not None:
        await repo.delete_project(session, replace)
    return project.id
