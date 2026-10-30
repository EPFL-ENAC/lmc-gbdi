"""The overview of a real project against what Excel computed from the same workbook.

Runs when the CSV export of openbdf_at_v2.0.0.xlsx (project AT-09) sits in
OPENBDF_DATA_DIR or backend/data/openbdf; the export is not committed.
Totals: the workbook's cached "Building carbon overview" cells. Elements: the same
sheet after Excel recalculated it (its cached element cells predate the codes).
"""

import os
from pathlib import Path

import pytest

from app.overview.repo import read_project
from app.overview.service import build_overview, material_rollup, stage_gwp

DATA_DIR = Path(
    os.environ.get("OPENBDF_DATA_DIR", Path(__file__).parents[1] / "data" / "openbdf")
)

pytestmark = pytest.mark.skipif(
    not (DATA_DIR / "bill_of_materials.csv").exists(),
    reason="no OpenBDF export in OPENBDF_DATA_DIR",
)

STAGES = {
    "a1_a3": 634581.0426407706,
    "a4_a5": 23109.077973525957,
    "b1_b8": 33010.08131827447,
    "c1_c4": 589914.0391065966,
}
ELEMENTS = {  # kg CO₂ eq, as Excel shows them rounded
    "1.1 Foundations and piling": (190534, 3086, -8898, 37438, "A1–A3", 0.86),
    "2.1 Frame": (151617, 4579, -8280, 118610, "A1–A3", 0.57),
    "2.2 Upper floors": (64155, 4223, -11746, 420063, "C1–C4", 0.88),
    "2.5 External envelope including roof finishes": (
        110422,
        8023,
        46467,
        4666,
        "A1–A3",
        0.65,
    ),
    "2.7 Internal walls": (40329, 148, 0, 1908, "A1–A3", 0.95),
}
MATERIALS = {  # (material, EPD product): (GWP, mass)
    ("Stahlbeton C25/30", "Beton der Druckfestigkeitsklasse C25/30"): (
        358948.6890979356,
        4522330.644718703,
    ),
    ("Estrich", "Zementestrich"): (133450.69732756514, 650143.8427278629),
    ("Leichtbeton", "Beton der Druckfestigkeitsklasse C20/25"): (
        16163.887429099723,
        233281.59662909858,
    ),
    ("Kies", "Kies (Korngröße 2/32)"): (10563.834475709606, 816817.1100320596),
    ("Splitt 2/15", "Splitt 2/15"): (6914.530817241489, 346697.9960556933),
}


@pytest.fixture(scope="module")
def project():
    return read_project(DATA_DIR)


@pytest.fixture(scope="module")
def overview(project):
    return build_overview(project)


def test_rows_and_headline_match_the_workbook(overview):
    assert overview.rows_read == 7494
    h = overview.headline
    assert h.whole_life == pytest.approx(1280614.2410391676, rel=1e-9)
    assert h.upfront == pytest.approx(657690.1206142965, rel=1e-9)
    assert h.per_m2_useful == pytest.approx(272.4131548689997, rel=1e-9)
    assert h.per_m2_gross == pytest.approx(234.93198331300084, rel=1e-9)
    assert h.per_m2_useful_per_year == pytest.approx(5.448263097379994, rel=1e-9)
    assert h.module_d1 == pytest.approx(-209782.211595777, rel=1e-9)


def test_stages_match_the_workbook(overview):
    assert {s.key: s.gwp for s in overview.stages} == pytest.approx(STAGES, rel=1e-9)


def test_elements_match_the_recalculated_sheet(overview):
    got = {
        e.element: (
            *(round(v) for v in e.gwp_by_stage.values()),
            e.dominant_stage,
            round(e.dominant_share, 2),
        )
        for e in overview.element_stages
    }
    assert got == ELEMENTS


def test_material_pairs_match_the_workbook(project, overview):
    # The sheet ranks only its five database lines; the API ranks every pair, so
    # compare the pairs' sums, not their rank.
    pairs = material_rollup([(row, stage_gwp(row)) for row in project.rows])
    for pair, (gwp, mass) in MATERIALS.items():
        assert float(pairs[pair]["gwp"]) == pytest.approx(gwp, rel=1e-9)
        assert float(pairs[pair]["mass"]) == pytest.approx(mass, rel=1e-9)
    assert overview.material_hotspots[0].share == pytest.approx(0.2803, abs=1e-4)


def test_module_checks_match_the_workbook(overview):
    # Cells F27 and F28: A1 is declared but only A1–A3 carries results.
    assert overview.modules_declared_without_result == 1
    assert overview.modules_with_undeclared_result == 0
    assert [c.module for c in overview.module_checks if c.status != "ok"] == ["A1"]


def test_benchmarks_and_use_per_year(overview):
    # B1–B8 (cell C37) over the 50-year study period.
    assert overview.use_per_year == pytest.approx(33010.08131827447 / 50, rel=1e-9)
    assert {b.key: b.band for b in overview.benchmarks} == {
        "leti": "A",  # 234.9 per m² gross floor area
        "re2020": "Within the 2031 ceiling",  # 272.4 per m² useful floor area
    }
