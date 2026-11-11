"""The overview rules, on a small invented project with hand-computed totals."""

import csv
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app
from app.overview.repo import BOM_FIELDS, GWP_FIELDS, PMD_FIELDS, read_project
from app.overview.schemas import ModuleCheck
from app.overview.service import (
    MODULES,
    BasisUnavailable,
    build_overview,
    in_element,
    on_basis,
    scope_label,
    study_period,
    text,
)

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


def write_project(directory: Path, rows=ROWS, data_types=None, general=GENERAL) -> Path:
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
        directory / "general_information.csv", ["field_code", "value"], general.items()
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
    assert overview.headline.per_m2_gross_per_year == pytest.approx(0.59 / 50)


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


AT_09 = ("A1–A3", "A4", "A5", "B1", "B2", "B3", "C1", "C2", "C3", "C4")
CHILE = ("A1–A3", "A1", "A2", "A3", "A4", "A5", "C1", "C2", "C3", "C4")


@pytest.mark.parametrize(
    ("declared", "results", "label"),
    [
        (AT_09, ("A1–A3", "A4", "A5", "B1", "C1"), "A–C · whole life"),
        # 45 Chilean buildings: no B declared, yet their totals carry a B2 result.
        (CHILE, ("A1–A3", "A4", "A5", "B2", "C3"), "A1–A5, C1–C4"),
        ((), ("A1", "A3"), "A1–A3 · cradle to gate"),  # nothing declared: the results
        (("A1–A3", "A5.2"), ("B6",), "A1–A5 · upfront"),
        (("A4", "B6"), (), "A4–A5, B1–B8"),
    ],
)
def test_the_scope_names_the_declared_stages(declared, results, label):
    checks = [
        ModuleCheck(
            module=name,
            declared=name in declared,
            has_result=name in results,
            status="ok",
        )
        for name, _, _ in MODULES
    ]
    assert scope_label(checks) == label


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


def test_each_ranking_carries_the_other_measure(overview):
    """The passport ranks by mass or by carbon and draws both for the same ten."""
    by_carbon, by_mass = overview.material_hotspots[0], overview.mass_hotspots[0]
    assert by_carbon.share_of_mass == pytest.approx(350 / overview.total_mass_kg)
    assert (by_mass.gwp, by_mass.share) == (65, pytest.approx(65 / 118))


def test_materials_list_every_material_the_top_tens_draw_from(overview):
    """What "show the remaining materials" expands: all of them, by carbon."""
    every = [(m.material, m.epd_product) for m in overview.materials]
    top = [(m.material, m.epd_product) for m in overview.material_hotspots]
    assert every[: len(top)] == top
    assert {(m.material, m.epd_product) for m in overview.mass_hotspots} <= set(every)


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
    assert len(fields) == 29
    assert fields["project_id"] == "TEST-1"
    assert fields["project_country"] is None


def test_title_block_lists_the_fourteen_fields_in_the_issue_order(overview):
    codes = [f.code for f in overview.title_block]
    assert len(codes) == 14
    assert codes[:3] == ["project_id", "project_country", "building_use_type"]
    assert codes[-1] == "lca_lci_modeling_approach"
    assert overview.title_block[0].value == "TEST-1"


def test_material_hotspots_carry_their_stage_split(overview):
    concrete = overview.material_hotspots[0]
    assert concrete.gwp_by_stage == {"a1_a3": 36, "a4_a5": 11, "b1_b8": 6, "c1_c4": 12}
    assert overview.mass_other_share == 0  # three materials, all in the top 10


def test_use_stage_is_spread_over_the_study_period(overview):
    assert overview.time.use_per_year == pytest.approx(4 / 50)


def test_the_placeholder_project_id_is_not_declared():
    assert text({"project_id": "XXXXXXX"}, "project_id") is None
    assert text({"project_id": "AT-09"}, "project_id") == "AT-09"


@pytest.mark.parametrize(
    ("declared", "years"),
    [("50", 50), ("60 years", 60), (" 60 Years ", 60), ("50 yr", 50), ("", None)],
)
def test_study_period_reads_a_number_of_years(declared, years):
    """OpenBDF types the study period as text: "60 years" declares 60."""
    assert study_period({"lca_reference_study_period": declared}) == years


def test_a_study_period_without_a_number_is_refused():
    with pytest.raises(ValueError, match="study period"):
        study_period({"lca_reference_study_period": "the building's life"})


# The fixture: 200 m² GFA, 100 m² UFA, 50 years.
@pytest.mark.parametrize(
    ("basis", "carbon", "mass", "unit"),
    [
        ("total", 1, 1, "kg CO₂e"),
        ("gfa", 200, 200, "kg CO₂e per m² GFA"),
        ("ufa", 100, 100, "kg CO₂e per m² UFA"),
        ("gfa_year", 200 * 50, 200, "kg CO₂e per m² GFA and year"),
    ],
)
def test_a_basis_divides_carbon_and_mass(overview, basis, carbon, mass, unit):
    o = on_basis(overview, basis)
    assert o.units.basis == basis and o.units.carbon == unit
    assert o.headline.whole_life == pytest.approx(118 / carbon)
    assert o.headline.module_d1 == pytest.approx(overview.headline.module_d1 / carbon)
    for kind in ("stages", "elements", "material_hotspots", "materials"):
        for got, total in zip(getattr(o, kind), getattr(overview, kind), strict=True):
            assert got.gwp == pytest.approx(total.gwp / carbon)
    for got, total in zip(o.element_stages, overview.element_stages, strict=True):
        assert got.gwp_by_stage == pytest.approx(
            {k: v / carbon for k, v in total.gwp_by_stage.items()}
        )
    assert o.not_classified.gwp == pytest.approx(overview.not_classified.gwp / carbon)
    # Mass is per area, never per year; so are the Time section's figures.
    assert o.total_mass_kg == pytest.approx(overview.total_mass_kg / mass)
    assert o.mass_hotspots[0].mass_kg == pytest.approx(
        overview.mass_hotspots[0].mass_kg / mass
    )
    assert o.material_classes[0].mass_kg == pytest.approx(
        overview.material_classes[0].mass_kg / mass
    )
    assert o.time.upfront == pytest.approx(overview.time.upfront / mass)
    assert o.time.use_per_year == pytest.approx(4 / 50 / mass)


def test_a_basis_leaves_shares_and_intensities(overview):
    o = on_basis(overview, "gfa_year")
    assert o.headline.upfront_share == overview.headline.upfront_share
    assert [s.share for s in o.stages] == [s.share for s in overview.stages]
    assert [m.share for m in o.materials] == [m.share for m in overview.materials]
    assert [m.gwp_per_kg for m in o.materials] == [
        m.gwp_per_kg for m in overview.materials
    ]
    assert [m.share_of_mass for m in o.materials] == [
        m.share_of_mass for m in overview.materials
    ]
    assert o.data_types == overview.data_types
    assert o.units.intensity == "kg CO₂e per kg and year"


def test_per_m2_gfa_matches_the_headline_figure(overview):
    # The float division of the cache against the Decimal one of the headline.
    assert on_basis(overview, "gfa").headline.whole_life == pytest.approx(
        overview.headline.per_m2_gross, rel=1e-12
    )
    assert on_basis(overview, "gfa_year").headline.whole_life == pytest.approx(
        overview.headline.per_m2_gross_per_year, rel=1e-12
    )


def test_a_basis_the_building_cannot_serve_is_refused(tmp_path):
    general = {"project_id": "TEST-2", "building_gross_floor_area": "200"}
    o = build_overview(read_project(write_project(tmp_path, general=general)))
    options = {b.key: b for b in o.bases}
    assert [k for k, b in options.items() if b.available] == ["total", "gfa"]
    assert options["ufa"].reason == "The workbook declares no useful floor area."
    assert options["gfa_year"].reason == "The workbook declares no study period."
    for basis in ("ufa", "gfa_year"):
        with pytest.raises(BasisUnavailable, match="declares no"):
            on_basis(o, basis)
    # None stays None: no study period, no use per year, on any basis.
    assert on_basis(o, "gfa").time.use_per_year is None
