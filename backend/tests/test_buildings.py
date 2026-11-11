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

from app.buildings.ingest import Finding, RejectedWorkbook, blocked_parts
from app.buildings.models import Upload
from app.buildings.repo import as_text, general_of, material_row
from app.buildings.service import compared, draft_summary, summary
from app.overview.repo import GWP_FIELDS, read_project
from app.overview.service import build_overview, declared
from tests.test_overview import write_project


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
