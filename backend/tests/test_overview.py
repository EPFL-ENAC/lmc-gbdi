"""The overview rules, on a small invented project with hand-computed totals."""

import csv
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app
from app.overview.repo import BOM_FIELDS, GWP_FIELDS, PMD_FIELDS, read_project
from app.overview.service import build_overview, in_element

# id, repetition, element, material, epd product, mass, GWP fields
ROWS = [
    # A1–A3 total given; A5 given. Counts 3 times.
    ("M1", "3", "2.1", "Concrete", "C25/30", "100",
     {"gwp_total_a1_a3": "10", "gwp_total_a4": "1", "gwp_total_a5": "2",
      "gwp_total_c3": "4", "gwp_total_d1": "-5", "gwp_f_a1_a3": "9"}),
    # A1–A3 blank: A1+A2+A3. A5 blank: A5.1–A5.4. Repetition 0 counts once.
    ("M2", "0", "2.1.3", "Concrete", "C25/30", "50",
     {"gwp_total_a1": "1", "gwp_total_a2": "2", "gwp_total_a3": "3",
      "gwp_total_a5_1": "1", "gwp_total_a5_4": "1", "gwp_total_b6": "6",
      "gwp_total_b6_1": "1000"}),
    # Element given with its name. Repetition blank counts once.
    ("M3", "", "1.1 Foundations and piling", "Steel", "Rebar", "20",
     {"gwp_total_a1_a3": "40", "gwp_total_b4": "-2", "gwp_f_a1_a3": "30"}),
    # No element, no material name.
    ("M4", "", "", "", "Window", "5", {"gwp_total_a1_a3": "15"}),
]  # fmt: skip
# Whole life: M1 (10+1+2+4)*3=51, M2 6+2+6=14, M3 40-2=38, M4 15 → 118.

GENERAL = {
    "project_id": "TEST-1",
    "building_useful_floor_area": "100",
    "building_gross_floor_area": "200",
    "lca_reference_study_period": "50",
}


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def write_project(directory: Path, rows=ROWS, data_types=None) -> Path:
    wide_fields = [*GWP_FIELDS, "gwp_total_b6_1"]
    write_csv(
        directory / "bill_of_materials.csv",
        list(BOM_FIELDS),
        [[r[0], r[1], r[2], r[3], r[4], r[5]] for r in rows],
    )
    write_csv(
        directory / "lca_results_wide.csv",
        ["material_id", *wide_fields],
        [[r[0], *(r[6].get(f, "") for f in wide_fields)] for r in rows],
    )
    write_csv(
        directory / "general_information.csv", ["field_code", "value"], GENERAL.items()
    )
    write_csv(
        directory / "project_material_database.csv",
        list(PMD_FIELDS),
        [[m, e, t] for (m, e), t in (data_types or {}).items()],
    )
    return directory


@pytest.fixture
def overview(tmp_path):
    data_types = {("Concrete", "C25/30"): "Generic (generic data from a database)"}
    return build_overview(read_project(write_project(tmp_path, data_types=data_types)))


def test_stages_apply_repetition_and_fallbacks(overview):
    gwp = {stage.key: stage.gwp for stage in overview.stages}
    assert gwp == {
        "a1_a3": 30 + 6 + 40 + 15,
        "a4_a5": 9 + 2,
        "b1_b8": 6 - 2,
        "c1_c4": 12,
    }


def test_whole_life_excludes_module_d_and_b_submodules(overview):
    assert overview.headline.whole_life == 118
    assert overview.headline.module_d1 == -15
    assert overview.headline.upfront == 91 + 11


def test_per_m2_figures_divide_by_floor_area_then_period(overview):
    assert overview.headline.per_m2_useful == pytest.approx(1.18)
    assert overview.headline.per_m2_gross == pytest.approx(0.59)
    assert overview.headline.per_m2_useful_per_year == pytest.approx(1.18 / 50)


def test_elements_follow_openbdf_order_and_keep_the_unclassified_visible(overview):
    assert [(e.element, e.gwp) for e in overview.elements] == [
        ("1.1 Foundations and piling", 38),
        ("2.1 Frame", 65),
    ]
    assert (overview.not_classified.gwp, overview.other_classified.gwp) == (15, 0)
    assert overview.not_classified.share == pytest.approx(15 / 118)


def test_dominant_stage_divides_by_the_element_total(overview):
    frame = overview.element_stages[1]
    assert frame.dominant_stage == "A1–A3"
    assert frame.dominant_share == pytest.approx(36 / 65)


@pytest.mark.parametrize(
    ("row_element", "matches"),
    [("2.1", True), ("2.1.3", True), ("2.1 Frame", True), ("2.10", False), ("", False)],
)
def test_element_codes_match_by_prefix(row_element, matches):
    assert in_element(row_element, "2.1") is matches


def test_hotspots_group_material_and_epd_product(overview):
    top = overview.material_hotspots[0]
    assert (top.material, top.epd_product) == ("Concrete", "C25/30")
    assert (top.gwp, top.mass_kg) == (65, 350)
    assert top.share == pytest.approx(65 / 118)
    assert top.gwp_per_kg == pytest.approx(65 / 350)
    assert overview.material_hotspots[-1].material == ""  # unnamed rows stay listed
    assert [m.material for m in overview.mass_hotspots] == ["Concrete", "Steel", ""]


def test_data_types_weigh_by_gwp_fossil_and_report_the_undeclared(overview):
    shares = {d.key: d.share for d in overview.data_types}
    assert overview.data_type_weighting == "gwp_fossil_a1_a3"
    assert shares["generic"] == pytest.approx(27 / 57)
    assert shares["undeclared"] == pytest.approx(30 / 57)


def test_unmatched_results_fail_loudly(tmp_path):
    write_project(tmp_path)
    wide = tmp_path / "lca_results_wide.csv"
    wide.write_text(wide.read_text().replace("M4,", "M9,"), encoding="utf-8")
    with pytest.raises(ValueError, match="disagree on material_id"):
        read_project(tmp_path)


def test_duplicate_material_ids_fail_loudly(tmp_path):
    with pytest.raises(ValueError, match="appears twice"):
        read_project(write_project(tmp_path, rows=[ROWS[0], ROWS[0]]))


def test_endpoint_serves_the_overview(tmp_path):
    settings = Settings(
        DB_URL="postgresql+psycopg://x:x@localhost/x",
        OPENBDF_DATA_DIR=write_project(tmp_path),
    )
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        response = TestClient(app).get("/api/overview")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["headline"]["whole_life"] == 118


def test_endpoint_says_when_no_project_is_configured():
    settings = Settings(
        DB_URL="postgresql+psycopg://x:x@localhost/x", OPENBDF_DATA_DIR=None
    )
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        response = TestClient(app).get("/api/overview")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503
