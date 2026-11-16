"""The database adapter: OpenBDF records → the overview's field-code text."""

import asyncio
import os
import pickle
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from openbdf.model.enums.countries import Country
from openbdf.model.enums.element_classifications import (
    OpenBDFBuildingElementClassification as Element,
)
from openbdf.model.enums.materials import OpenBDFMaterialClassification as Material
from openbdf.model.tables import ProjectRecord

from app.buildings.ingest import (
    TOTAL_NOTE,
    WHAT_TO_DO,
    WHAT_TO_DO_BY_CODE,
    WORDING,
    Finding,
    RejectedWorkbook,
    blocked_parts,
)
from app.buildings.models import Upload
from app.buildings.repo import as_text, general_of, material_row
from app.buildings.service import (
    comparability,
    compared,
    draft_summary,
    reject_summary,
    summary,
)
from app.overview.repo import GWP_FIELDS, read_project
from app.overview.service import build_overview, declared
from tests.test_overview import GENERAL, ROWS, write_project


def test_as_text_reads_like_the_workbook():
    assert as_text(None) == ""
    assert as_text(True) == "TRUE"
    assert as_text(False) == "FALSE"
    assert as_text(Country("aut")) == "Austria"
    assert as_text(Decimal("5451")) == "5451"


def test_scope_flags_reach_declared():
    general = general_of(ProjectRecord(lca_a1_3=True, lca_a1=None))
    assert declared(general, "lca_a1_3")
    assert not declared(general, "lca_a1")


def line(**changes):
    values = {
        "material_id": "m1",
        "repetition": None,
        "element": Element("2.1"),
        "custom": " Beton ",
        "dataset": "C30/37",
        "mass": Decimal("10"),
        "material_class": Material("4.2"),
        "element_custom": " 2E.01 Wand ",
        "wide_id": 7,
    } | changes
    gwp = tuple(Decimal(i) for i, _ in enumerate(GWP_FIELDS))
    return (*values.values(), *gwp)


def test_material_row_from_a_stored_line():
    row = material_row(line())
    assert row.element == "2.1"
    assert row.pair == ("Beton", "C30/37")
    assert row.repetition == 1  # blank counts once
    assert row.material_class == "4.2 Concrete"
    assert row.element_custom == "2E.01 Wand"
    assert row.gwp[GWP_FIELDS[3]] == 3


def test_a_line_without_wide_results_is_an_error():
    with pytest.raises(ValueError, match="no Wide results"):
        material_row(line(wide_id=None))


def test_summary_and_compared_build_from_an_overview(tmp_path):
    """Both API shapes validate: a field added to a schema but not filled is a 500."""
    o = build_overview(read_project(write_project(tmp_path)))
    upload = Upload(
        project_record_id=1,
        file_name="T.xlsx",
        uploaded_at=datetime.now(UTC),
        findings=[],
    )
    s = summary(upload, o)
    assert (s.useful_floor_area_m2, s.study_period_years) == (100, 50)
    assert compared(upload, o).gross_floor_area_m2 == 200


def test_a_compared_building_carries_its_declared_boundary_and_method(tmp_path):
    """Side by side, each column says what it covers."""
    general = {
        **GENERAL,
        "lca_cycle_system_boundary": "Cradle to Grave + Module D",
        "lcia_methodology": "EN 15804:2012+A2:2019",
    }
    o = build_overview(read_project(write_project(tmp_path, general=general)))
    upload = Upload(
        project_record_id=1, file_name="T.xlsx", uploaded_at=datetime.now(UTC)
    )
    c = compared(upload, o)
    assert (c.system_boundary, c.lcia_methodology) == (
        "Cradle to Grave + Module D",
        "EN 15804:2012+A2:2019",
    )


def with_module_d(d1: str | None, d2: str | None):
    """ROWS with M1's module D results replaced (M1 counts 3 times)."""
    rows = []
    for r in ROWS:
        gwp = {
            k: v for k, v in r[6].items() if k not in ("gwp_total_d1", "gwp_total_d2")
        }
        if r[0] == "M1":
            gwp |= {k: v for k, v in (("gwp_total_d1", d1), ("gwp_total_d2", d2)) if v}
        rows.append((*r[:6], gwp))
    return rows


@pytest.mark.parametrize(
    ("d1", "d2", "declares_d", "module_d"),
    [
        ("-5", "2", False, (-5 + 2) * 3 / 200),  # results: D1 + D2, per m² GFA
        ("-5", "5", False, 0.0),  # they cancel, but the building has module D
        (None, None, True, None),  # declared, no result: no module D
        (None, "3", False, 3 * 3 / 200),  # D2 alone
        ("-5", None, False, -5 * 3 / 200),  # D1 alone
        (None, None, False, None),  # no module D at all: nothing, not 0
    ],
)
def test_module_d_is_d1_plus_d2_outside_the_total(
    tmp_path, d1, d2, declares_d, module_d
):
    general = {**GENERAL, "lca_d": "TRUE"} if declares_d else GENERAL
    o = build_overview(
        read_project(
            write_project(tmp_path, general=general, rows=with_module_d(d1, d2))
        )
    )
    upload = Upload(
        project_record_id=1, file_name="T.xlsx", uploaded_at=datetime.now(UTC)
    )
    c = compared(upload, o)
    assert c.module_d_per_m2 == module_d
    assert c.has_module_d is (module_d is not None)
    assert c.whole_life_per_m2 == 118 / 200  # never subtracted from A–C
    assert c.module_d1_per_m2 == (float(d1) * 3 / 200 if d1 else 0.0)


def test_a_declared_module_d_with_d1_and_d2_at_zero_is_not_present(tmp_path):
    # D declared, D1 and D2 written as 0 on M1: no module D on any page.
    rows = [
        (*r[:6], {**r[6], "gwp_total_d1": "0", "gwp_total_d2": "0"})
        if r[0] == "M1"
        else r
        for r in with_module_d(None, None)
    ]
    general = {**GENERAL, "lca_d": "TRUE", "lca_d1": "TRUE", "lca_d2": "TRUE"}
    (tmp_path / "d").mkdir()
    (tmp_path / "plain").mkdir()
    o = build_overview(
        read_project(write_project(tmp_path / "d", general=general, rows=rows))
    )
    plain = build_overview(
        read_project(write_project(tmp_path / "plain", general=GENERAL, rows=rows))
    )
    upload = Upload(
        project_record_id=1, file_name="T.xlsx", uploaded_at=datetime.now(UTC)
    )
    c = compared(upload, o)
    assert o.headline.module_d_present is False
    assert (o.headline.module_d1, o.headline.module_d2) == (0.0, 0.0)
    assert c.has_module_d is False
    assert c.module_d_per_m2 is None
    # The data checks flag module D as declared with no result, and nothing else.
    d = o.module_checks[-1]
    assert (d.module, d.declared, d.has_result) == ("D", True, False)
    assert d.status == "declared_no_result"
    assert o.module_checks[:-1] == plain.module_checks[:-1]
    assert (
        o.modules_declared_without_result == plain.modules_declared_without_result + 1
    )


@pytest.mark.parametrize(
    ("a", "b", "verdict"),
    [
        ("EN 15804:2012+A2:2019", "EN 15804:2012+A2:2019", "same_method"),
        # A1 leaves biogenic carbon out of the GWP total, A2 counts it in.
        ("EN 15804+A1", "EN 15804:2012+A2:2019", "methods_differ"),
        (None, "EN 15804:2012+A2:2019", "method_not_declared"),
        ("", "", "method_not_declared"),
    ],
)
def test_two_buildings_compare_only_within_one_method(a, b, verdict):
    assert comparability(a, b) == verdict


def reject(code, sheet):
    return {
        "code": code,
        "severity": "Reject",
        "sheet": sheet,
        "row": None,
        "message": "",
    }


@pytest.mark.parametrize(
    ("findings", "blocked"),
    [
        # Chile: results and materials of different lengths, paired by position only.
        ([reject("E05", "LCA Result (Wide)")], ["carbon"]),
        # OASE, TRIO: a required project field is missing; the figures still hold.
        ([reject("E01", "General Information")], []),
        ([reject("E01", "Bill of Materials")], ["carbon", "materials"]),
        ([{**reject("E25", "LCA Result (Wide)"), "severity": "Warning"}], []),
        ([reject("E99", None)], ["carbon", "materials"]),
        # The total checks judge only the declared total, which is never read.
        (
            [reject("E018", "LCA Result (Wide)"), reject("E019", "LCA Result (Wide)")],
            [],
        ),
        (
            [reject("E018", "LCA Result (Wide)"), reject("E005", "LCA Result (Wide)")],
            ["carbon"],
        ),
    ],
)
def test_a_draft_blocks_the_parts_its_rejects_touch(findings, blocked):
    assert blocked_parts(findings) == blocked


def test_a_carbon_blocked_draft_lists_without_figures():
    upload = Upload(
        project_record_id=3,
        file_name="X (DRAFT).xlsx",
        uploaded_at=datetime.now(UTC),
        findings=[reject("E05", "LCA Result (Wide)")],
        draft=True,
    )
    s = draft_summary(upload, {"project_name": "X", "project_country": "Chile"}, 115)
    assert (s.draft, s.blocked, s.whole_life, s.whole_life_per_m2) == (
        True,
        ["carbon"],
        None,
        None,
    )


def stored(code, message, count=1, severity="Reject"):
    return {
        "code": code,
        "severity": severity,
        "sheet": "LCA Result (Wide)",
        "row": None,
        "message": message,
        "count": count,
    }


def test_a_draft_sums_up_its_rejects_one_line_per_code():
    module_d = "Module D must not be added to the whole-life total"
    findings = [
        *(stored("E018", module_d) for _ in range(20)),
        stored("E018", "350 more E018 findings on this sheet", 350),
        *(
            stored("E019", f"gwp_total_total is {x}, the modules sum to 52.8")
            for x in "123"
        ),
        stored("E05", "Row 3: material_id a in the inventory, b in the results"),
        stored("E05", "Row 4: material_id c in the inventory, d in the results"),
        stored("E001", "Field project_country is required and was not provided"),
        stored("W002", "Row 5 has no mass", severity="Warning"),
    ]
    # E05 on the results sheet blocks the carbon, so no line says its figures stand.
    assert [tuple(r.model_dump().values()) for r in reject_summary(findings)] == [
        ("E018", 370, module_d, WHAT_TO_DO_BY_CODE["E018"]),
        ("E019", 3, WORDING["E019"], WHAT_TO_DO_BY_CODE["E019"]),
        (
            "E05",
            2,
            "For example: Row 3: material_id a in the inventory, b in the results",
            WHAT_TO_DO,
        ),
        (
            "E001",
            1,
            "Field project_country is required and was not provided",
            WHAT_TO_DO_BY_CODE["E001"],
        ),
    ]
    upload = Upload(
        project_record_id=4,
        file_name="D.xlsx",
        uploaded_at=datetime.now(UTC),
        findings=findings,
        draft=True,
    )
    assert draft_summary(upload, {}).reject_summary == reject_summary(findings)


def test_rejected_workbook_crosses_processes():
    # The parser process raises it; the API reads its findings for the 422.
    finding = Finding("E05", "Reject", "LCA Results", 3, "misaligned")
    back = pickle.loads(pickle.dumps(RejectedWorkbook([finding])))
    assert back.findings == [finding]


def test_a_killed_parser_process_is_replaced():
    """Out of memory kills the upload's process; the next upload still runs."""
    from concurrent.futures.process import BrokenProcessPool

    from app.buildings.routes import in_parser

    async def run():
        with pytest.raises(BrokenProcessPool):
            await in_parser(os._exit, 1)
        return await in_parser(abs, -3)

    assert asyncio.run(run()) == 3


def test_warm_up_skips_a_building_it_cannot_read(monkeypatch):
    """One unreadable building is logged; the others are still computed."""
    from app.buildings import repo, service

    uploads = [
        Upload(project_record_id=i, file_name="T.xlsx", uploaded_at=datetime.now(UTC))
        for i in (1, 2)
    ]
    read: list[int] = []

    async def list_uploads(_session):
        return uploads

    async def summary_of(_session, upload):
        if upload.project_record_id == 1:
            raise ValueError("unreadable")
        read.append(upload.project_record_id)

    monkeypatch.setattr(repo, "list_uploads", list_uploads)
    monkeypatch.setattr(service, "summary_of", summary_of)
    asyncio.run(service.warm_up())
    assert read == [2]


def upload(client, replace):
    files = {"file": ("AT-09.xlsx", b"workbook")}
    return client.post(f"/api/buildings?replace={replace}&draft=true", files=files)


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.db import get_session
    from app.main import app

    app.dependency_overrides[get_session] = lambda: None
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_replacing_an_unknown_building_is_404_before_the_parse(client, monkeypatch):
    from app.buildings import repo, routes

    async def get_upload(_session, project_id):
        raise repo.ProjectNotFound(project_id)

    async def in_parser(*_args):
        raise AssertionError("parsed")

    monkeypatch.setattr(repo, "get_upload", get_upload)
    monkeypatch.setattr(routes, "in_parser", in_parser)
    assert upload(client, 999).status_code == 404


def test_a_replace_is_kept_when_the_client_leaves(client, monkeypatch, tmp_path):
    """The old building is deleted already: deleting the new one would lose both."""
    from starlette.requests import Request

    from app.buildings import repo, routes, service

    new = summary(
        Upload(
            project_record_id=200,
            file_name="AT-09.xlsx",
            uploaded_at=datetime.now(UTC),
            findings=[],
        ),
        build_overview(read_project(write_project(tmp_path))),
    )
    calls: list[tuple] = []

    async def get_upload(_session, project_id):
        return None

    async def in_parser(fn, workbook, file_name, draft, replace):
        calls.append(("ingest", draft, replace))
        return new, None

    async def delete(_session, project_id):
        calls.append(("delete", project_id))

    async def left(_request):
        return True

    monkeypatch.setattr(repo, "get_upload", get_upload)
    monkeypatch.setattr(routes, "in_parser", in_parser)
    monkeypatch.setattr(service, "delete", delete)
    monkeypatch.setattr(
        service, "forget", lambda project_id: calls.append(("forget", project_id))
    )
    monkeypatch.setattr(service, "remember", lambda *_: calls.append(("remember",)))
    monkeypatch.setattr(Request, "is_disconnected", left)

    response = upload(client, 121)
    assert (response.status_code, response.json()["id"]) == (201, 200)
    assert calls == [("ingest", True, 121), ("forget", 121), ("remember",)]


def test_the_total_checks_say_the_figures_stand_only_when_carbon_is_shown():
    module_d = "Module D must not be added to the whole-life total"
    findings = [
        stored("E018", module_d),
        stored("E019", "gwp_total_total is 1, the modules sum to 52.8"),
    ]
    own = [WHAT_TO_DO_BY_CODE["E018"], WHAT_TO_DO_BY_CODE["E019"]]
    assert [r.what_to_do for r in reject_summary(findings)] == [
        t + TOTAL_NOTE for t in own
    ]
    # One more reject on the results sheet blocks the carbon: the note goes.
    blocked = [*findings, stored("E05", "Row 3: material_id a, b in the results")]
    assert [r.what_to_do for r in reject_summary(blocked)] == [*own, WHAT_TO_DO]


def test_each_code_says_what_to_do():
    def todo(*findings):
        return {r.code: r.what_to_do for r in reject_summary(list(findings))}

    assert todo(reject("E001", "Project Material Database"))["E001"] == (
        "Fill the field that the message names. Then upload the workbook again "
        "with replace."
    )
    e004 = (
        "Give each bill of materials row one row in LCA Result (Wide), in the "
        "same order."
    )
    assert todo(reject("E004", "LCA Result (Wide)"))["E004"] == e004 + (
        " The dashboard cannot pair the rows, so it shows no carbon for this draft."
    )
    assert todo(reject("E004", "General Information"))["E004"] == e004
    e018 = (
        "Take module D out of the declared total: the total covers the modules "
        "A to C only."
    )
    assert todo(reject("E018", "LCA Result (Wide)"))["E018"] == e018 + (
        " The dashboard adds the modules itself, so the figures shown stand."
    )
    assert (
        todo(reject("E018", "LCA Result (Wide)"), reject("E005", "LCA Result (Wide)"))[
            "E018"
        ]
        == e018
    )
    assert todo(reject("E020", "General Information"))["E020"] == (
        "Declare the reference study period in General Information. The workbook "
        "has results after stage A, and the per-year figures need the period."
    )
    assert todo(reject("E05", "LCA Result (Wide)"))["E05"] == (
        "Correct the workbook and upload it again with replace."
    )


def test_a_code_with_a_condensed_entry_takes_the_general_wording():
    """The first 20 messages name field a; the 5 condensed ones are not stored and
    may name another field, so one stored message cannot speak for all 25."""
    findings = [
        *(stored("E003", "Field a expects float") for _ in range(20)),
        stored("E003", "5 more E003 findings on this sheet", 5),
    ]
    (line,) = reject_summary(findings)
    assert (line.code, line.count, line.message) == ("E003", 25, WORDING["E003"])


def test_the_what_to_do_table_holds_the_agreed_texts():
    """Literal, so a typo in the table fails here."""
    database_line = (
        "Give each bill of materials material exactly one line in the project "
        "material database, with the same material_ref_id."
    )
    assert WHAT_TO_DO_BY_CODE == {
        "E001": "Fill the field that the message names. Then upload the workbook "
        "again with replace.",
        "E002": "Replace the value with one of the values that the field allows.",
        "E003": "Give the field that the message names a value of the right type, "
        "for example a number without a unit.",
        "E004": "Give each bill of materials row one row in LCA Result (Wide), in "
        "the same order.",
        "E005": "Give the bill of materials row and its results row the same "
        "material_id.",
        "E006": "Give the share a value from 0 to 100.",
        "E010": "Set the declared flag of the indicator to true, or remove its "
        "results.",
        "E011": "Remove the project material database line that no bill of "
        "materials material uses, or add the material.",
        "E012": database_line,
        "E013": database_line,
        "E014": database_line,
        "E015": "Give each project material database line its own material_ref_id.",
        "E016": "Give each bill of materials row its own material_id.",
        "E017": "Fill the aggregate stage or its sub-modules, not both. Example: "
        "A1–A3, or A1, A2 and A3.",
        "E018": "Take module D out of the declared total: the total covers the "
        "modules A to C only.",
        "E019": "Correct the declared total, or correct the module values that it "
        "adds.",
        "E020": "Declare the reference study period in General Information. The "
        "workbook has results after stage A, and the per-year figures need the "
        "period.",
    }
