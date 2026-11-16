from datetime import date

import pytest
from openbdf.model.enums.buildings import BuildingTypology
from openbdf.model.enums.countries import Country

from app.buildings.gbdi_id import country_code, format_id

START, END = date(2024, 3, 1), date(2026, 1, 15)
AUT, MFH = Country.AUT, BuildingTypology.MFH


@pytest.mark.parametrize(
    ("country", "start", "end", "typology", "number", "expected"),
    [
        (AUT, START, END, MFH, 53, "aut_2024_mfh_0053_v1"),
        (AUT, None, END, MFH, 53, "aut_2026_mfh_0053_v1"),
        (AUT, None, None, MFH, 53, "aut_xxx_mfh_0053_v1"),
        (None, START, END, MFH, 1, "xxx_2024_mfh_0001_v1"),
        (AUT, START, END, None, 1, "aut_2024_xxx_0001_v1"),
        (None, None, None, None, 1, "xxx_xxx_xxx_0001_v1"),
        ("aut", START, END, "mfh", 10000, "aut_2024_mfh_10000_v1"),
    ],
)
def test_the_id_of_each_part(country, start, end, typology, number, expected):
    assert format_id(country, start, end, typology, number, 1) == expected


def test_the_version_ends_the_id():
    assert format_id(AUT, START, END, MFH, 53, 2) == "aut_2024_mfh_0053_v2"


@pytest.mark.parametrize(
    ("value", "expected"),
    [("Atlantis", "xxx"), ("Austria", "xxx"), ("aut", "aut"), ("", "xxx")],
)
def test_only_an_alpha_3_code_is_a_country(value, expected):
    assert country_code(value) == expected
