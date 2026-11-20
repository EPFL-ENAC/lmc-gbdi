"""Two buildings compared: the case, the stages each one covers, and the figures on
the stages both cover. Every expected figure is computed by hand from the rows."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.buildings.models import Upload
from app.db import get_session
from app.main import app
from app.overview.repo import read_project
from app.overview.service import build_overview, on_basis
from tests.test_overview import GENERAL, NO_B, ROWS, write_project
from tests.test_overview_namings import named

METHOD = "EN 15804:2012+A2:2019"


@pytest.fixture
def client():
    app.dependency_overrides[get_session] = lambda: None
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def db(monkeypatch, tmp_path):
    """A fake database, project id → ProjectData, read the way the service reads it."""
    from app.buildings import repo, service

    stamp = datetime(2026, 11, 1, tzinfo=UTC)
    projects = {}

    def row(project_id):
        if project_id not in projects:
            raise repo.ProjectNotFound(project_id)
        return projects[project_id]

    async def get_upload(_session, project_id):
        row(project_id)
        return Upload(
            project_record_id=project_id,
            file_name=f"P{project_id}.xlsx",
            uploaded_at=stamp,
            findings=[],
        )

    async def uploaded_at(_session, project_id):
        row(project_id)
        return stamp

    async def read(_session, project_id, results=True):
        return row(project_id)

    monkeypatch.setattr(repo, "get_upload", get_upload)
    monkeypatch.setattr(repo, "uploaded_at", uploaded_at, raising=False)
    monkeypatch.setattr(repo, "read_project", read)
    monkeypatch.setattr(service, "_overviews", {})
    monkeypatch.setattr(service, "_drafts", {})

    def put(project_id, rows=ROWS, **general):
        directory = tmp_path / str(project_id)
        directory.mkdir()
        fields = {**GENERAL, "lcia_methodology": METHOD, **general}
        fields = {k: v for k, v in fields.items() if v is not None}
        projects[project_id] = named(
            read_project(write_project(directory, rows=rows, general=fields))
        )

    return put


def compare(client, query=""):
    response = client.get(f"/api/buildings/compare?a=1&b=2{query}")
    assert response.status_code == 200, response.text
    return response.json()


A_TO_C = ["A1–A3", "A4–A5", "B1–B8", "C1–C4"]
NO_B_STAGES = ["A1–A3", "A4–A5", "C1–C4"]


@pytest.fixture
def different(db):
    """a: ROWS on 200 m², every stage. b: ROWS without B on 100 m²."""
    db(1)
    db(2, rows=NO_B, building_gross_floor_area="100")


# Captured from the code before the scope parameter existed. Whole life: a 118 / 200,
# b 114 / 100. Elements: Foundations (M3) a 38, b 40; Frame (M1 + M2) a 65, b 59;
# Not classified (M4) 15. Materials: Concrete M1 + M2, Steel M3, mass 350, 20, 5.
PIN = {
    "a": {
        "id": 1,
        "file_name": "P1.xlsx",
        "project_name": None,
        "country": None,
        "gross_floor_area_m2": 200.0,
        "rows_read": 4,
        "scope": "A1–C",
        "lcia_methodology": METHOD,
        "system_boundary": None,
        "whole_life_per_m2": 0.59,
        "upfront_per_m2": 0.51,
        "module_d1_per_m2": -0.075,
        "has_module_d": True,
        "module_d_per_m2": -0.075,
        "project_reference": None,
        "project_doi": None,
    },
    "b": {
        "id": 2,
        "file_name": "P2.xlsx",
        "project_name": None,
        "country": None,
        "gross_floor_area_m2": 100.0,
        "rows_read": 4,
        "scope": "A1–A5, C1–C4",
        "lcia_methodology": METHOD,
        "system_boundary": None,
        "whole_life_per_m2": 1.14,
        "upfront_per_m2": 1.02,
        "module_d1_per_m2": -0.15,
        "has_module_d": True,
        "module_d_per_m2": -0.15,
        "project_reference": None,
        "project_doi": None,
    },
    "comparability": "same_method",
    "ratio": 1.9322033898305084,
    "stages": [
        {"label": "A1–A3", "a": 0.455, "b": 0.91},
        {"label": "A4–A5", "a": 0.055, "b": 0.11},
        {"label": "B1–B8", "a": 0.02, "b": 0.0},
        {"label": "C1–C4", "a": 0.06, "b": 0.12},
    ],
    "elements": [
        {"label": "1.1 Foundations and piling", "a": 0.19, "b": 0.4},
        {"label": "2.1 Frame", "a": 0.325, "b": 0.59},
        {"label": "Not classified", "a": 0.075, "b": 0.15},
    ],
    "material_carbon": [
        {"label": "4.2 Concrete", "a": 0.325, "b": 0.59},
        {"label": "5.1 Steel", "a": 0.19, "b": 0.4},
        {"label": "Not classified", "a": 0.075, "b": 0.15},
    ],
    "material_mass": [
        {"label": "4.2 Concrete", "a": 1.75, "b": 3.5},
        {"label": "5.1 Steel", "a": 0.1, "b": 0.2},
        {"label": "Not classified", "a": 0.025, "b": 0.05},
    ],
}


def test_without_scope_every_existing_field_is_as_before(client, different):
    out = compare(client)
    assert {k: out[k] for k in PIN} == PIN
    assert out["method_note"].startswith("A2: biogenic INCLUDED")


def test_different_stages_name_what_each_covers_and_what_is_left_out(client, different):
    out = compare(client)
    assert out["case"] == "different_stages"
    assert out["covered_a"] == A_TO_C
    assert out["covered_b"] == NO_B_STAGES
    assert out["common_stages"] == NO_B_STAGES
    # B1–B8 of a: M2 B6 6 + M3 B4 -2 = 4, over 200 m².
    assert out["left_out"] == [{"stage": "B1–B8", "not_covered_by": "b", "value": 0.02}]
    assert out["applied_scope"] == "own"  # no parameter: today's figures


def test_same_stages_merge_with_no_toggle(client, db):
    db(1)
    db(2, building_gross_floor_area="100")
    out = compare(client)
    assert out["case"] == "same_stages"
    assert out["covered_a"] == out["covered_b"] == out["common_stages"] == A_TO_C
    assert out["left_out"] == []
    assert out["applied_scope"] == "common"
    assert compare(client, "&scope=own")["applied_scope"] == "common"


@pytest.mark.parametrize("method", ["EN 15804:2012+A1:2013", None])
def test_another_or_no_method_is_not_comparable(client, db, method):
    db(1)
    db(2, rows=NO_B, lcia_methodology=method)
    out = compare(client, "&scope=common")
    assert out["case"] == "methods_differ"
    assert out["applied_scope"] == "own"
    assert out["stages"] == compare(client)["stages"]  # the parameter is ignored


def test_two_buildings_without_a_common_stage_are_not_comparable(client, db):
    db(1, rows=[("M1", "", "", "", "Slab", "1", {"gwp_total_a1_a3": "10"})])
    db(2, rows=[("M1", "", "", "", "Slab", "1", {"gwp_total_c3": "4"})])
    out = compare(client, "&scope=common")
    assert out["case"] == "no_common_stages"
    assert out["common_stages"] == []
    assert out["applied_scope"] == "own"
    assert out["left_out"] == [
        {"stage": "A1–A3", "not_covered_by": "b", "value": 0.05},
        {"stage": "C1–C4", "not_covered_by": "a", "value": 0.02},
    ]


def test_common_scope_sums_the_common_stages_only(client, different):
    out = compare(client, "&scope=common")
    assert out["applied_scope"] == "common"
    # a without B (M2 B6 6, M3 B4 -2): 91 + 11 + 12 = 114 over 200; b 114 over 100.
    assert out["a"]["whole_life_per_m2"] == pytest.approx(0.57)
    assert out["b"]["whole_life_per_m2"] == pytest.approx(1.14)
    assert out["ratio"] == pytest.approx(2.0)
    assert out["a"]["upfront_per_m2"] == pytest.approx(0.51)  # (91 + 11) / 200
    assert out["stages_a"] == out["stages_b"] == out["ratio_stages"] == NO_B_STAGES
    assert out["upfront_stages"] == ["A1–A3", "A4–A5"]
    assert out["stages"] == [
        {"label": "A1–A3", "a": 0.455, "b": 0.91},
        {"label": "A4–A5", "a": 0.055, "b": 0.11},
        {"label": "C1–C4", "a": 0.06, "b": 0.12},
    ]


def test_own_scope_is_the_answer_without_a_scope(client, different):
    own = compare(client, "&scope=own")
    assert own == compare(client)
    assert own["applied_scope"] == "own"
    assert own["stages_a"] == A_TO_C
    assert own["stages_b"] == NO_B_STAGES
    assert own["ratio_stages"] is None
    assert own["a"]["whole_life_per_m2"] == 0.59  # 118 / 200, B included


def approx_rows(rows):
    return [{**r, "a": pytest.approx(r["a"]), "b": pytest.approx(r["b"])} for r in rows]


def test_elements_and_materials_sum_their_common_stages(client, different):
    out = compare(client, "&scope=common")
    # a: Frame M1 (10 + 1 + 2 + 4) × 3 = 51, M2 6 + 2 = 8 without B6: 59 / 200.
    # Foundations M3 40 without B4 -2: 40 / 200. M4 15 / 200. b is NO_B on 100 m².
    assert out["elements"] == approx_rows(
        [
            {"label": "1.1 Foundations and piling", "a": 0.2, "b": 0.4},
            {"label": "2.1 Frame", "a": 0.295, "b": 0.59},
            {"label": "Not classified", "a": 0.075, "b": 0.15},
        ]
    )
    assert out["material_carbon"] == approx_rows(
        [
            {"label": "4.2 Concrete", "a": 0.295, "b": 0.59},
            {"label": "5.1 Steel", "a": 0.2, "b": 0.4},
            {"label": "Not classified", "a": 0.075, "b": 0.15},
        ]
    )
    assert out["material_mass"] == PIN["material_mass"]  # mass has no stage
    for side in "ab":
        total = out[side]["whole_life_per_m2"]
        assert sum(r[side] for r in out["elements"]) == pytest.approx(total)
        assert sum(r[side] for r in out["material_carbon"]) == pytest.approx(total)


@pytest.mark.parametrize("scope", ["", "&scope=common", "&scope=own"])
def test_module_d_is_never_inside_a_total(client, different, scope):
    out = compare(client, scope)
    # D1 -5 × 3 on M1, on its own line in every scope.
    assert out["a"]["module_d_per_m2"] == -0.075
    assert out["b"]["module_d_per_m2"] == -0.15
    stages = sum(r["a"] for r in out["stages"])
    assert out["a"]["whole_life_per_m2"] == pytest.approx(stages)
    assert all(r["label"] != "D" for r in out["stages"])


def one_per_stage(a1_a3, a4, b, c3, b_field="gwp_total_b4"):
    return [
        ("M1", "", "", "", "A", "1", {"gwp_total_a1_a3": a1_a3}),
        ("M2", "", "", "", "B", "1", {"gwp_total_a4": a4}),
        ("M3", "", "", "", "C", "1", {b_field: b}),
        ("M4", "", "", "", "D", "1", {"gwp_total_c3": c3}),
    ]


def test_the_example_pair_compares_on_the_stages_both_declare(client, db):
    """Buildings 53 and 1 of the live data, per m² × 100 on 100 m². b declares A and
    C only, and carries a stray B2 result: it does not cover B1–B8."""
    area = {"building_gross_floor_area": "100"}
    db(1, rows=one_per_stage("-13832.34", "392.22", "-216.32", "29923.15"), **area)
    flags = {f"lca_{m}": "1" for m in ("a1_3", "a4", "a5", "c1", "c2", "c3", "c4")}
    b_rows = one_per_stage("-3402.70", "2069.34", "8.27", "24480.62", "gwp_total_b2")
    db(2, rows=b_rows, **area, **flags)
    own = compare(client)
    assert own["case"] == "different_stages"
    assert own["covered_b"] == NO_B_STAGES
    assert own["a"]["whole_life_per_m2"] == pytest.approx(162.6671)
    assert own["b"]["whole_life_per_m2"] == pytest.approx(231.5553)  # B2 included
    common = compare(client, "&scope=common")
    # a: -138.3234 + 3.9222 + 299.2315; b: -34.0270 + 20.6934 + 244.8062.
    assert common["a"]["whole_life_per_m2"] == pytest.approx(164.8303)
    assert common["b"]["whole_life_per_m2"] == pytest.approx(231.4726)
    assert common["ratio"] == pytest.approx(231.4726 / 164.8303)
    assert common["left_out"] == [
        {"stage": "B1–B8", "not_covered_by": "b", "value": pytest.approx(-2.1632)}
    ]


def test_same_declared_stages_leave_a_stray_result_out_of_the_merged_figures(
    client, db
):
    """Both declare A and C. b also carries a B2 result it does not declare: on one
    axis its figures hold only the stages the labels name."""
    area = {"building_gross_floor_area": "100"}
    flags = {f"lca_{m}": "1" for m in ("a1_3", "a4", "a5", "c1", "c2", "c3", "c4")}
    db(1, rows=one_per_stage("100", "10", "0", "50"), **area, **flags)
    db(2, rows=one_per_stage("200", "20", "8", "30", "gwp_total_b2"), **area, **flags)
    merged = compare(client, "&scope=common")
    assert merged["case"] == "same_stages"
    # a: (100 + 10 + 50) / 100; b: (200 + 20 + 30) / 100, without the stray 8.
    assert merged["a"]["whole_life_per_m2"] == pytest.approx(1.6)
    assert merged["b"]["whole_life_per_m2"] == pytest.approx(2.5)
    assert merged["ratio"] == pytest.approx(2.5 / 1.6)
    assert merged["ratio_stages"] == NO_B_STAGES
    # Without the parameter the figures are those of before, the stray 8 inside,
    # so the ratio names no stages.
    before = compare(client)
    assert before["b"]["whole_life_per_m2"] == pytest.approx(2.58)
    assert before["ratio_stages"] is None


def test_an_unknown_scope_is_refused(client, different):
    assert client.get("/api/buildings/compare?a=1&b=2&scope=all").status_code == 422


def test_stage_figures_add_up_and_follow_the_basis(tmp_path):
    o = build_overview(named(read_project(write_project(tmp_path))))
    per_m2 = on_basis(o, "gfa")  # 200 m²
    buckets = (*o.elements, o.other_classified, o.not_classified)
    for row in (*buckets, *o.material_classes):
        assert sum(row.gwp_by_stage.values()) == pytest.approx(row.gwp)
    for row, scaled in zip(o.material_classes, per_m2.material_classes, strict=True):
        assert scaled.gwp_by_stage == pytest.approx(
            {k: v / 200 for k, v in row.gwp_by_stage.items()}
        )
