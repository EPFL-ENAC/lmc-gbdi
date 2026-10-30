"""Workbook → OpenBDF records → database, through lmc-openbdf's own parser.

The same path for the upload endpoint and scripts/load_buildings.py. Parsing a COLA
workbook takes 15–60 s of CPU, so the endpoint runs `parse` in a worker thread.
"""

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

from app.buildings.models import ProjectRecord, Upload


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str  # Info | Warning | Reject
    sheet: str | None
    row: int | None
    message: str


class RejectedWorkbook(Exception):
    """Reject findings: nothing is stored, as `openbdf open` saves nothing."""

    def __init__(self, findings: list[Finding]):
        super().__init__(f"{len(findings)} findings, some of them rejects")
        self.findings = findings


def finding(f: OpenBDFValidationError) -> Finding:
    return Finding(f.code, f.severity.value, f.source, f.row, f.message)


def parse(workbook: bytes) -> tuple[ProjectRecord, list[Finding]]:
    """The lmc-openbdf README's ingest: translate, convert, validate."""
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
    project = project_package_from_tables(tables, translator, findings=findings)
    dropped = frozenset(
        f.row for f in findings if isinstance(f, DroppedLine) and f.row is not None
    )
    findings += validate_project(
        project, tables, document_translator=translator, dropped_rows=dropped
    )
    found = [finding(f) for f in sort_findings(findings)]
    if any(f.severity == Severity.REJECT.value for f in found):
        raise RejectedWorkbook(found)
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
) -> int:
    """Add the project graph and its upload row; the caller commits."""
    session.add(project)
    await session.flush()
    assert project.id is not None
    session.add(
        Upload(
            project_record_id=project.id,
            file_name=Path(file_name).name,
            uploaded_at=datetime.now(UTC),
            findings=[f.__dict__ for f in findings],
        )
    )
    await session.flush()
    return project.id
