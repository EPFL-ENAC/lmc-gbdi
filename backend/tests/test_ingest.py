"""Ingest without a database: findings are condensed and grouped, and a replace
deletes the old building only once the new one is stored.

The stage test reads the gwp_total flags from gwp_total_mapping.tsv, taken from
the v2.0.0 field mapping. A second test compares that file with the gitignored
workbook in backend/data/reference-v2.0.0/ (or GBDI_REFERENCE_DIR), and skips
without it.
"""

import asyncio
import os
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from openbdf.model.enums.buildings import BuildingTypology
from openbdf.model.enums.countries import Country

from app.buildings import ingest, repo, service
from app.buildings.ingest import EXAMPLES, Finding, RejectedWorkbook, condense
from app.buildings.models import ProjectRecord, Upload
from app.overview.repo import GWP_FIELDS, MaterialRow
from app.overview.service import stage_gwp

REFERENCE = Path(
    os.environ.get(
        "GBDI_REFERENCE_DIR", Path(__file__).parents[1] / "data" / "reference-v2.0.0"
    )
)
MAPPING = next(REFERENCE.glob("openbdf_field to standard mapping*.xlsx"), None)
FIXTURE = Path(__file__).with_name("gwp_total_mapping.tsv")


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

    # store now reads the old upload and the counter, which the fake session lacks.
    numbers(monkeypatch, old_upload("xxx", 7, 1))
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


def old_upload(country: str, number: int, version: int) -> Upload:
    return Upload(
        project_record_id=121,
        file_name="AT-09.xlsx",
        uploaded_at=datetime(2026, 1, 1, tzinfo=UTC),
        findings=[],
        gbdi_id="old",
        gbdi_country=country,
        gbdi_number=number,
        gbdi_version=version,
    )


def numbers(monkeypatch, old: Upload | None = None) -> dict[str, int]:
    """A counter per country, as gbdi_counter keeps them, the locked old upload, and
    a delete that does nothing."""
    counters: dict[str, int] = {"aut": 52}

    async def next_number(_session, country):
        counters[country] = counters.get(country, 0) + 1
        return counters[country]

    async def locked_upload(_session, _project_id):
        assert old is not None
        return old

    async def delete_project(_session, _project_id):
        pass

    monkeypatch.setattr(repo, "next_number", next_number)
    monkeypatch.setattr(repo, "locked_upload", locked_upload)
    monkeypatch.setattr(repo, "delete_project", delete_project)
    return counters


def stored_id(country: Country | None, replace: int | None = None) -> str:
    session = Session()
    project = ProjectRecord(
        project_country=country,
        building_construction_start_date=date(2024, 3, 1),
        building_use_type=BuildingTypology.MFH,
    )
    asyncio.run(ingest.store(session, project, "x.xlsx", [], False, replace))
    upload = session.added[1]
    assert upload.gbdi_id.endswith(f"_{upload.gbdi_number:04d}_v{upload.gbdi_version}")
    return upload.gbdi_id


def test_each_new_building_takes_its_countrys_next_number(monkeypatch):
    counters = numbers(monkeypatch)
    assert stored_id(Country.AUT) == "aut_2024_mfh_0053_v1"
    assert stored_id(Country.AUT) == "aut_2024_mfh_0054_v1"
    assert stored_id(None) == "xxx_2024_mfh_0001_v1"
    assert counters == {"aut": 54, "xxx": 1}


def test_a_replace_in_the_same_country_keeps_the_number_one_version_up(monkeypatch):
    counters = numbers(monkeypatch, old_upload("aut", 53, 1))
    assert stored_id(Country.AUT, replace=121) == "aut_2024_mfh_0053_v2"
    assert counters == {"aut": 52}  # the counter is not called


def test_a_replace_to_another_country_takes_that_countrys_number(monkeypatch):
    counters = numbers(monkeypatch, old_upload("aut", 53, 3))
    assert stored_id(Country.CHE, replace=121) == "che_2024_mfh_0001_v1"
    assert counters == {"aut": 52, "che": 1}


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


def fixture_flags() -> dict[str, tuple[bool, bool]]:
    """Field -> (sum into whole life A–C, in upfront A1–A5), from the fixture."""
    header, *lines = FIXTURE.read_text().splitlines()
    assert header == "field\twhole_life\tupfront"
    flags = {}
    for line in lines:
        field, whole_life, upfront = line.split("\t")
        assert {whole_life, upfront} <= {"true", "false"}, line
        assert field not in flags, field
        flags[field] = (whole_life == "true", upfront == "true")
    return flags


def workbook_flags() -> dict[str, tuple[bool, bool]]:
    from openpyxl import load_workbook

    rows = load_workbook(MAPPING, read_only=True, data_only=True).worksheets[0]
    header, *lines = rows.iter_rows(values_only=True)
    column = {name: i for i, name in enumerate(header)}
    return {
        line[1]: (
            line[column["Sum into whole-life A–C"]] is True,
            line[column["In upfront A1–A5"]] is True,
        )
        for line in lines
        if str(line[1]).startswith("gwp_total")
    }


def test_the_stages_add_exactly_the_modules_the_mapping_sums():
    """The field mapping says which gwp_total fields go into the whole life (A–C)
    and the upfront (A1–A5); D and the across-stage total go into neither."""
    flags = fixture_flags()
    assert {f for f in GWP_FIELDS if f.startswith("gwp_total")} <= flags.keys()
    whole_life = {field for field, (whole, _) in flags.items() if whole}
    upfront = {field for field, (_, up) in flags.items() if up}

    # Each field a power of two: a sum names exactly the fields it took.
    gwp = {field: Decimal(2**i) for i, field in enumerate(GWP_FIELDS)}
    row = MaterialRow("m", "", ("", ""), Decimal(1), Decimal(0), gwp)
    stages = stage_gwp(row)
    assert sum(stages.values()) == sum(gwp[f] for f in whole_life)
    assert stages["a1_a3"] + stages["a4_a5"] == sum(gwp[f] for f in upfront)


def test_the_fixture_matches_the_mapping_workbook():
    """A new mapping version shows here as drift from gwp_total_mapping.tsv."""
    if MAPPING is None:
        pytest.skip(f"no field mapping in {REFERENCE}")
    assert fixture_flags() == workbook_flags()
