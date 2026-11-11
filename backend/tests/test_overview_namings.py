"""The names toggle: every element and material figure under the OpenBDF
classification and under the project's own names, and mass by element."""

from dataclasses import replace

import pytest

from app.overview.repo import BOM_FIELDS, ProjectData, read_project
from app.overview.service import build_overview, on_basis
from tests.test_overview import ROWS, write_csv, write_project

# id: (bec_custom, OpenBDF material class). M5 has mass and no carbon.
NAMES = {
    "M1": ("2E.01 Außenwand", "4.2 Concrete"),
    "M2": ("2D.01 Decken", "4.2 Concrete"),
    "M3": ("2C.03 Gründung", "5.1 Steel"),
    "M4": ("", ""),
    "M5": ("2E.02 Innenwand", "4.2 Concrete"),
}
M5 = ("M5", "", "2.7", "Gypsum", "Plasterboard", "30", {})


def named(data: ProjectData, names=NAMES) -> ProjectData:
    rows = [
        replace(
            r,
            element_custom=names.get(r.material_id, ("", ""))[0],
            material_class=names.get(r.material_id, ("", ""))[1],
        )
        for r in data.rows
    ]
    return replace(data, rows=rows)


@pytest.fixture
def overview(tmp_path):
    return build_overview(
        named(read_project(write_project(tmp_path, rows=[*ROWS, M5])))
    )


def bars(view):
    return [*view.elements, view.other_classified, view.not_classified]


@pytest.mark.parametrize("naming", ["openbdf", "custom"])
def test_the_element_bars_add_up_to_the_carbon_and_the_mass(overview, naming):
    view = overview.namings[naming]
    assert sum(e.gwp for e in bars(view)) == pytest.approx(118)
    assert sum(e.mass_kg for e in bars(view)) == pytest.approx(405)
    assert overview.total_mass_kg == 405
    assert sum(e.share_of_mass for e in bars(view)) == pytest.approx(1)


@pytest.mark.parametrize("naming", ["openbdf", "custom"])
def test_the_materials_within_an_element_add_up_to_its_mass(overview, naming):
    view = overview.namings[naming]
    # A bucket without mass has no fold: nothing would be in it.
    folded = [e for e in bars(view) if e in view.elements or e.mass_kg]
    assert [m.element for m in view.element_materials] == [e.element for e in folded]
    for element, within in zip(folded, view.element_materials, strict=True):
        parts = [*within.materials, *([within.other] if within.other else [])]
        assert within.mass_kg == pytest.approx(element.mass_kg)
        assert sum(m.mass_kg for m in parts) == pytest.approx(element.mass_kg)


def test_custom_elements_group_by_bec_custom_in_label_order(overview):
    view = overview.namings["custom"]
    assert [(e.element, e.gwp, e.mass_kg) for e in view.elements] == [
        ("2C.03 Gründung", 38, 20),
        ("2D.01 Decken", 14, 50),
        ("2E.01 Außenwand", 51, 300),
        ("2E.02 Innenwand", 0, 30),
    ]
    assert (view.not_classified.gwp, view.not_classified.mass_kg) == (15, 5)


def test_openbdf_elements_carry_their_mass(overview):
    view = overview.namings["openbdf"]
    assert [(e.element, e.gwp, e.mass_kg) for e in view.elements] == [
        ("1.1 Foundations and piling", 38, 20),
        ("2.1 Frame", 65, 350),
        ("2.7 Internal walls", 0, 30),
    ]
    assert view.elements[1].share_of_mass == pytest.approx(350 / 405)


def test_an_element_with_mass_and_no_carbon_has_no_stage_row(overview):
    view = overview.namings["openbdf"]
    assert [e.element for e in view.element_stages] == [
        "1.1 Foundations and piling",
        "2.1 Frame",
    ]


def test_openbdf_materials_group_by_class(overview):
    view = overview.namings["openbdf"]
    concrete = view.material_hotspots[0]
    assert (concrete.material, concrete.epd_product) == ("4.2 Concrete", "")
    assert (concrete.gwp, concrete.mass_kg) == (65, 380)
    assert concrete.gwp_per_kg == pytest.approx(65 / 380)
    assert concrete.gwp_by_stage == {"a1_a3": 36, "a4_a5": 11, "b1_b8": 6, "c1_c4": 12}
    assert [m.material for m in view.mass_hotspots] == [
        "4.2 Concrete",
        "5.1 Steel",
        "Not classified",
    ]
    frame = view.element_materials[1]
    assert [(m.material, m.mass_kg) for m in frame.materials] == [("4.2 Concrete", 350)]


def test_elements_after_the_eighth_go_to_other_classified(tmp_path):
    ids = [f"N{i}" for i in range(10)]
    rows = [(i, "", "2.1", "Brick", "B", "1", {"gwp_total_a1_a3": "1"}) for i in ids]
    labels = {i: (f"C{9 - n:02}", "") for n, i in enumerate(ids)}  # C09 … C00
    data = named(read_project(write_project(tmp_path, rows=rows)), labels)
    view = build_overview(data).namings["custom"]
    assert [e.element for e in view.elements] == [f"C{n:02}" for n in range(8)]
    assert (view.other_classified.gwp, view.other_classified.mass_kg) == (2, 2)
    # Every row is classified, so "Not classified" has no fold.
    assert view.element_materials[-1].element == "Other classified elements"


def test_the_bars_go_to_the_largest_elements_not_the_first_ones(tmp_path):
    # C00 to C03 come first in label order but are small; C04 to C11 are larger.
    rows = [
        (f"N{n}", "", "2.1", "Brick", "B", "1", {"gwp_total_a1_a3": str(n + 1)})
        for n in range(12)
    ]
    labels = {f"N{n}": (f"C{n:02}", "") for n in range(12)}
    data = named(read_project(write_project(tmp_path, rows=rows)), labels)
    view = build_overview(data).namings["custom"]
    assert [e.element for e in view.elements] == [f"C{n:02}" for n in range(4, 12)]
    assert view.other_classified.gwp == 1 + 2 + 3 + 4


def test_a_mass_only_element_does_not_take_the_bar_of_a_carbon_one(tmp_path):
    gwp = {"gwp_total_a1_a3": "1"}
    carbon = [(f"N{n}", "", "2.1", "Brick", "B", "1", gwp) for n in range(8)]
    labels = {f"N{n}": (f"C{n + 1:02}", "") for n in range(8)}
    labels["MASS"] = ("C00", "")  # first in label order, no carbon
    rows = [*carbon, ("MASS", "", "2.1", "Gypsum", "G", "500", {})]
    view = build_overview(
        named(read_project(write_project(tmp_path, rows=rows)), labels)
    ).namings["custom"]
    assert [e.element for e in view.elements] == [f"C{n:02}" for n in range(1, 9)]
    assert [e.element for e in view.element_stages] == [
        e.element for e in view.elements
    ]


def test_an_element_named_like_a_bucket_keeps_its_own_fold(tmp_path):
    gwp = {"gwp_total_a1_a3": "1"}
    rows = [
        ("N1", "", "2.1", "Brick", "B", "10", gwp),
        ("N2", "", "2.1", "Steel", "S", "5", gwp),
    ]
    labels = {"N1": ("Not classified", ""), "N2": ("", "")}
    view = build_overview(
        named(read_project(write_project(tmp_path, rows=rows)), labels)
    ).namings["custom"]
    assert [(m.element, m.mass_kg) for m in view.element_materials] == [
        ("Not classified", 10),
        ("Not classified", 5),
    ]


def test_one_material_left_over_is_shown_not_folded(tmp_path):
    gwp = {"gwp_total_a1_a3": "1"}
    rows = [(f"N{n}", "", "2.1", f"M{n}", "", str(10 - n), gwp) for n in range(6)]
    within = build_overview(read_project(write_project(tmp_path, rows=rows)))
    frame = within.namings["custom"].element_materials[-1]
    assert [m.material for m in frame.materials] == [f"M{n}" for n in range(6)]
    assert frame.other is None


def test_a_heavy_element_lists_five_materials_and_the_rest_as_one_row(tmp_path):
    gwp = {"gwp_total_a1_a3": "1"}
    rows = [(f"N{n}", "", "2.1", f"M{n}", "", str(10 - n), gwp) for n in range(7)]
    within = build_overview(read_project(write_project(tmp_path, rows=rows)))
    # No bec_custom: under the custom names, every row is in the last bar.
    frame = within.namings["custom"].element_materials[-1]
    assert (frame.element, frame.mass_kg) == ("Not classified", 49)
    assert [m.material for m in frame.materials] == [f"M{n}" for n in range(5)]
    assert frame.other.material == "2 other materials"
    assert frame.other.mass_kg == 5 + 4
    assert frame.other.share == pytest.approx(9 / 49)


def test_the_top_level_fields_are_the_views_they_come_from(overview):
    for o in (overview, on_basis(overview, "gfa")):
        elements, materials = o.namings["openbdf"], o.namings["custom"]
        assert o.elements == elements.elements
        assert o.not_classified == elements.not_classified
        assert o.element_stages == elements.element_stages
        assert o.materials == materials.materials
        assert o.mass_hotspots == materials.mass_hotspots


def test_the_csv_reader_reads_the_custom_element(tmp_path):
    write_project(tmp_path)
    write_csv(
        tmp_path / "bill_of_materials.csv",
        [*BOM_FIELDS, "bec_custom"],
        [[*r[:6], " 2E.01 Wand "] for r in ROWS],
    )
    assert {r.element_custom for r in read_project(tmp_path).rows} == {"2E.01 Wand"}


def flat(value, path=""):
    """Every leaf of a dumped model, by its path: "/elements/0/gwp" → 65."""
    if isinstance(value, dict):
        items = value.items()
    elif isinstance(value, list):
        items = enumerate(value)
    else:
        return {path: value}
    return {p: v for k, x in items for p, v in flat(x, f"{path}/{k}").items()}


# The fixture: 200 m² GFA, 100 m² UFA, 50 years.
@pytest.mark.parametrize(
    ("basis", "carbon", "mass"),
    [("gfa", 200, 200), ("ufa", 100, 100), ("gfa_year", 200 * 50, 200)],
)
def test_a_basis_divides_every_figure_of_both_views(tmp_path, basis, carbon, mass):
    """Walks every field, so a figure that on_basis forgets fails here. Six more
    materials without bec_custom fill the "other materials" row of the custom
    "Not classified" bar."""
    extra = [(f"X{n}", "", "2.1", f"Extra {n}", "", "1", {}) for n in range(6)]
    data = read_project(write_project(tmp_path, rows=[*ROWS, M5, *extra]))
    overview = build_overview(named(data))
    assert overview.namings["custom"].element_materials[-1].other is not None

    def divisor(path: str) -> float:
        if path.endswith("/gwp") or "/gwp_by_stage/" in path:
            return carbon
        return mass if path.endswith("/mass_kg") else 1

    total = flat(overview.model_dump()["namings"])
    expected = {
        p: v / divisor(p) if isinstance(v, float) else v for p, v in total.items()
    }
    got = flat(on_basis(overview, basis).model_dump()["namings"])
    assert got == pytest.approx(expected)
