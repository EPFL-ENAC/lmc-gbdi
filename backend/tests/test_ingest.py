"""Ingest without a database: openbdf reads the workbook, its findings are condensed
and grouped, and a replace deletes the old building only once the new one is stored.

The reference tests read the gitignored v2.0.0 reference workbook (AT-09) and its
field mapping from backend/data/reference-v2.0.0/, and skip without them.
"""

import asyncio
import io
from collections import Counter
from decimal import Decimal
from pathlib import Path

import pytest
from openpyxl import Workbook

from app.buildings import ingest, repo, service
from app.buildings.ingest import EXAMPLES, Finding, RejectedWorkbook, condense, parse
from app.buildings.models import ProjectRecord
from app.buildings.repo import as_text, general_of, material_row
from app.overview.repo import GWP_FIELDS, MaterialRow, ProjectData
from app.overview.service import build_overview, stage_gwp

REFERENCE = Path(__file__).parents[1] / "data" / "reference-v2.0.0"
WORKBOOK = REFERENCE / "openbdf_at_v2.0.0.xlsx"
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
    assert service.findings_count(findings, "W004") == 42


def row_sheet(workbook: Workbook, title: str, codes: list, rows: list) -> None:
    """A row sheet of the specification: old codes on row 3, updated codes on row 4,
    data from row 14."""
    sheet = workbook.create_sheet(title)
    sheet.cell(3, 1, "Field Code")
    sheet.cell(4, 1, "UPDATED Field Code")
    for column, (old, new) in enumerate(codes, start=2):
        sheet.cell(3, column, old)
        sheet.cell(4, column, new)
    for offset, row in enumerate(rows):
        for column, value in enumerate(row, start=2):
            sheet.cell(14 + offset, column, value)


def specification_workbook() -> bytes:
    workbook = Workbook()
    general = workbook.active
    general.title = "General Information"
    # Codes in columns G and H, values in column Q.
    general.cell(1, 7, "Field Code")
    general.cell(1, 8, "UPDATED Field Code")
    general.cell(2, 7, "project_name")
    general.cell(2, 17, "Spec project")
    nameless = [f"MAT-{i}" for i in range(3, 28)]  # 25 lines that carry nothing
    row_sheet(
        workbook,
        "Bill of Materials",
        [
            ("material_id", None),
            ("material_name_custom", "custom_material_name"),
            ("bec_custom", None),
            ("bec_openbdf", None),
            ("material_weight_kg", None),
        ],
        [
            # As in AT-09: the national code has no mapping, so openbdf keeps the
            # workbook's own element code, a number cell.
            ["MAT-1", "Concrete", "2E.01 Aussenwandkonstruktionen", 2.1, 100],
            ["MAT-2", None, None, None, 500],  # nameless, with a mass and results
            *([material_id] for material_id in nameless),
        ],
    )
    row_sheet(
        workbook,
        "LCA Result (Wide)",
        [
            ("material_id", None),
            ("gwp_total_a1_a3", None),
            ("gwp_total_d1", None),
            ("gwp_total_total", None),
        ],
        [
            ["MAT-1", 10, 2, 12],  # the total adds module D
            ["MAT-2", 5, None, 5],
            *([material_id, 0] for material_id in nameless),
        ],
    )
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_a_specification_workbook_keeps_its_named_lines_and_drops_the_others():
    project, found = parse(specification_workbook(), draft=True)

    [concrete] = project.bill_of_materials
    assert (concrete.material_id, concrete.bec_openbdf.value) == ("MAT-1", "2.1")
    assert concrete.lca_results_full_record is not None
    counts = Counter()
    for f in found:
        counts[f.code] += f.count
    assert (counts["W005"], counts["W012"], counts["W013"]) == (26, 1, 1)
    [carried] = [f for f in found if f.code == "W012"]
    assert carried.row == 15
    # 26 dropped lines: 20 with their rows, one entry for the other 6.
    assert [f.count for f in found if f.code == "W005"] == [1] * EXAMPLES + [6]
    # Its rejects are required project fields left blank: no figure is blocked.
    assert {f.sheet for f in found if f.severity == "Reject"} == {"General Information"}
    assert ingest.blocked_parts([f.__dict__ for f in found]) == []


def test_without_draft_the_same_workbook_is_rejected():
    with pytest.raises(RejectedWorkbook):
        parse(specification_workbook())


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


def project_data(record) -> ProjectData:
    """What repo.read_project reads back once the parsed project is stored."""

    def values(line) -> tuple:
        wide = line.lca_results_full_record
        gwp = (None if wide is None else getattr(wide, f) for f in GWP_FIELDS)
        return (
            line.material_id,
            line.floor_repetition,
            line.bec_openbdf,
            line.custom_material_name,
            line.lca_dataset_material_name,
            line.material_weight_kg,
            line.common_material_name,
            line.bec_custom,
            None if wide is None else 0,  # the Wide id, which only the database gives
            *gwp,
        )

    return ProjectData(
        general=general_of(record),
        rows=[material_row(values(line)) for line in record.bill_of_materials],
        data_types={
            (
                (m.custom_material_name or "").strip(),
                (m.lca_dataset_material_name or "").strip(),
            ): as_text(m.material_data_type)
            for m in record.project_material_database
        },
    )


@pytest.fixture(scope="module")
def reference():
    if not WORKBOOK.exists():
        pytest.skip(f"no reference workbook at {WORKBOOK}")
    return parse(WORKBOOK.read_bytes(), draft=True)  # about 30 s


def test_the_reference_workbook_drops_its_nameless_lines(reference):
    record, found = reference
    assert len(record.bill_of_materials) == 5890
    counts = Counter()
    for f in found:
        counts[f.code] += f.count
    assert (counts["W005"], counts["W012"], counts["W013"]) == (1604, 310, 18115)
    # Required in the specification, blank in the workbook: AT-09 is a draft.
    assert [(f.sheet, f.row) for f in found if f.severity == "Reject"] == [
        ("General Information", 4),
        ("General Information", 23),
    ]
    assert ingest.blocked_parts([f.__dict__ for f in found]) == []


def test_the_reference_workbook_ingests_to_the_kept_lines_figures(reference):
    """The workbook's figures less the 1 604 dropped lines (310 carried 203 491 kg)."""
    o = build_overview(project_data(reference[0]))
    h = o.headline
    assert h.whole_life == pytest.approx(1077122.8565416648, rel=1e-9)
    assert h.upfront == pytest.approx(525062.425206049, rel=1e-9)
    assert h.module_d1 == pytest.approx(-169182.6763776832, rel=1e-9)
    assert h.module_d2 == 0
    assert o.total_mass_kg == pytest.approx(8029442.029785348, rel=1e-9)
    assert {s.key: round(s.gwp, 2) for s in o.stages} == {
        "a1_a3": 511783.62,
        "a4_a5": 13278.81,
        "b1_b8": -31201.83,
        "c1_c4": 583262.26,
    }
    assert {e.element: (round(e.gwp), round(e.share, 4)) for e in o.elements} == {
        "1.1 Foundations and piling": (222160, 0.2063),
        "2.1 Frame": (266525, 0.2474),
        "2.2 Upper floors": (476694, 0.4426),
        "2.5 External envelope including roof finishes": (27965, 0.026),
        "2.7 Internal walls": (42385, 0.0394),
    }
    assert round(o.not_classified.gwp) == 41394


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
