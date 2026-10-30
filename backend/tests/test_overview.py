"""The overview rules, on a small invented project with hand-computed totals."""

import csv
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app
from app.overview.benchmarks import SCALES, band_of
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
    assert overview.headline.upfront_share == pytest.approx(102 / 118)
    assert overview.total_mass_kg == 350 + 20 + 5


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


def test_module_checks_compare_flags_with_results(tmp_path):
    flags = {"lca_a1_3": "TRUE", "lca_a4": "1", "lca_c1": "TRUE", "lca_b6": "FALSE"}
    write_project(tmp_path)
    general = tmp_path / "general_information.csv"
    rows = [*GENERAL.items(), *flags.items()]
    write_csv(general, ["field_code", "value"], rows)
    status = {
        c.module: c.status for c in build_overview(read_project(tmp_path)).module_checks
    }
    assert status["A1–A3"] == "ok"  # declared, M1 has a result
    assert status["A4"] == "ok"
    assert status["C1"] == "declared_no_result"
    assert status["B6"] == "result_not_declared"  # M2 has B6, flag says FALSE
    assert status["A2"] == "result_not_declared"  # M2 has A2, no flag at all
    assert status["A5.2"] == "ok"  # neither declared nor present


def test_project_fields_keep_blanks_as_not_declared(overview):
    fields = {f.code: f.value for f in overview.project_fields}
    assert len(fields) == 22
    assert fields["project_id"] == "TEST-1"
    assert fields["project_country"] is None


def test_material_hotspots_carry_their_stage_split(overview):
    concrete = overview.material_hotspots[0]
    assert concrete.gwp_by_stage == {"a1_a3": 36, "a4_a5": 11, "b1_b8": 6, "c1_c4": 12}
    assert overview.mass_other_share == 0  # three materials, all in the top 10


def test_use_stage_is_spread_over_the_study_period(overview):
    assert overview.use_per_year == pytest.approx(4 / 50)


def test_benchmarks_place_the_project_on_each_scale(overview):
    bands = {b.key: (b.value, b.band) for b in overview.benchmarks}
    assert bands["leti"] == (pytest.approx(0.59), "A++")  # per m² gross
    assert bands["re2020"] == (pytest.approx(1.18), "Within the 2031 ceiling")


@pytest.mark.parametrize(
    ("value", "inclusive", "band"),
    [(299.9, False, "A"), (300, False, "B"), (1200, False, "Beyond G")],
)
def test_leti_bands_are_upper_exclusive(value, inclusive, band):
    assert band_of(value, SCALES[0][7], inclusive) == band


def test_re2020_ceilings_are_inclusive():
    assert band_of(490, SCALES[1][7], True) == "Within the 2031 ceiling"
    assert band_of(740.1, SCALES[1][7], True) == "Above the 2022 ceiling"
