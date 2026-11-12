"""Ingest without a database: findings are condensed and grouped, and a replace
deletes the old building only once the new one is stored.

The mapping test reads the gitignored v2.0.0 field mapping from
backend/data/reference-v2.0.0/, and skips without it.
"""

import asyncio
from decimal import Decimal
from pathlib import Path

import pytest

from app.buildings import ingest, repo, service
from app.buildings.ingest import EXAMPLES, Finding, RejectedWorkbook, condense
from app.buildings.models import ProjectRecord
from app.overview.repo import GWP_FIELDS, MaterialRow
from app.overview.service import stage_gwp

REFERENCE = Path(__file__).parents[1] / "data" / "reference-v2.0.0"
MAPPING = next(REFERENCE.glob("openbdf_field to standard mapping*.xlsx"), None)


def warning(code: str, row: int, sheet: str = "Bill of Materials") -> Finding:
    return Finding(code, "Warning", sheet, row, f"row {row}")


def test_findings_beyond_the_examples_become_one_entry_with_a_count():
    many = [warning("W004", row) for row in range(EXAMPLES + 25)]
    one_more = [warning("W001", row) for row in range(EXAMPLES + 1)]
    other_sheet = [warning("W004", 1, "LCA Result (Wide)")]
    kept = condense(many + one_more + other_sheet)

    assert kept[:EXAMPLES] == many[:EXAMPLES]
    assert kept[EXAMPLES] == Finding(
        "W004",
        "Warning",
        "Bill of Materials",
        None,
        "25 more W004 findings on this sheet",
        25,
    )
    # An entry for one finding would hide its row: it is kept as it is.
    assert kept[EXAMPLES + 1 : 2 * EXAMPLES + 2] == one_more
    assert kept[-1] == other_sheet[0]
    assert sum(f.count for f in kept) == len(many + one_more + other_sheet)


def test_groups_put_rejects_first_then_the_most_frequent():
    findings = [
        {**warning("W001", 3).__dict__},  # stored before the count existed
        {**warning("W004", 1).__dict__, "count": 1},
        {**warning("W004", 0).__dict__, "row": None, "count": 40},
        {**warning("W004", 9).__dict__, "sheet": "LCA Result (Wide)", "count": 1},
        {**Finding("E001", "Reject", "General Information", 4, "").__dict__},
    ]
    groups = service.finding_groups(findings)
    assert [(g.code, g.sheet, g.count) for g in groups] == [
        ("E001", "General Information", 1),
        ("W004", "Bill of Materials", 41),
        ("W001", "Bill of Materials", 1),
        ("W004", "LCA Result (Wide)", 1),
    ]
    assert [(f.row, f.count) for f in groups[1].examples] == [(1, 1), (None, 40)]
    assert service.findings_count(findings) == 44


class Session:
    """Records what store asks of the database; a flush gives the project its id."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.added: list = []

    def add(self, record) -> None:
        self.calls.append(f"add {type(record).__name__}")
        self.added.append(record)

    async def flush(self) -> None:
        self.calls.append("flush")
        self.added[0].id = 200


def test_a_replace_deletes_the_old_building_after_storing_the_new_one(monkeypatch):
    session = Session()
    project = ProjectRecord(project_name="AT-09")

    async def delete_project(_session, project_id):
        session.calls.append(f"delete {project_id}")

    monkeypatch.setattr(repo, "delete_project", delete_project)
    stored = asyncio.run(ingest.store(session, project, "AT-09.xlsx", [], True, 121))
    assert stored == 200
    assert session.calls == [
        "add ProjectRecord",
        "flush",
        "add Upload",
        "flush",
        "delete 121",
    ]


def test_a_rejected_replace_deletes_nothing(monkeypatch):
    deleted: list[int] = []

    def rejected(_workbook, _draft):
        raise RejectedWorkbook([Finding("E001", "Reject", None, None, "")])

    async def delete_project(_session, project_id):
        deleted.append(project_id)

    monkeypatch.setattr(service, "parse", rejected)
    monkeypatch.setattr(repo, "delete_project", delete_project)
    with pytest.raises(RejectedWorkbook):
        service.ingest(b"", "AT-09.xlsx", False, 121)
    assert deleted == []


def test_the_stages_add_exactly_the_modules_the_mapping_sums():
    """The field mapping says which gwp_total fields go into the whole life (A–C)
    and the upfront (A1–A5); D and the across-stage total go into neither."""
    if MAPPING is None:
        pytest.skip(f"no field mapping in {REFERENCE}")
    from openpyxl import load_workbook

    rows = load_workbook(MAPPING, read_only=True, data_only=True).worksheets[0]
    header, *lines = rows.iter_rows(values_only=True)
    column = {name: i for i, name in enumerate(header)}
    total = [line for line in lines if str(line[1]).startswith("gwp_total")]
    whole_life = {
        line[1] for line in total if line[column["Sum into whole-life A–C"]] is True
    }
    upfront = {line[1] for line in total if line[column["In upfront A1–A5"]] is True}

    # Each field a power of two: a sum names exactly the fields it took.
    gwp = {field: Decimal(2**i) for i, field in enumerate(GWP_FIELDS)}
    row = MaterialRow("m", "", ("", ""), Decimal(1), Decimal(0), gwp)
    stages = stage_gwp(row)
    assert sum(stages.values()) == sum(gwp[f] for f in whole_life)
    assert stages["a1_a3"] + stages["a4_a5"] == sum(gwp[f] for f in upfront)
