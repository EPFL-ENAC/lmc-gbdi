"""The database adapter: OpenBDF records → the overview's field-code text."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from openbdf.model.enums.countries import Country
from openbdf.model.enums.element_classifications import (
    OpenBDFBuildingElementClassification as Element,
)
from openbdf.model.enums.materials import OpenBDFMaterialClassification as Material
from openbdf.model.tables import ProjectRecord

from app.buildings.models import Upload
from app.buildings.repo import as_text, general_of, material_row
from app.buildings.service import compared, summary
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
