"""The project id the dashboard gives each building (org#108).

`<country>_<year>_<typology>_<number>_v<version>`, for example `aut_2024_mfh_0053_v1`:
the ISO 3166-1 alpha-3 code of `project_country`, the year construction started (else
ended), the `building_use_type` code, a number per country and the version, raised by
each replace. A part the workbook does not give is `xxx`. Separate from the
`project_id` the workbook declares.
"""

from datetime import date

from openbdf.model.enums.buildings import BuildingTypology
from openbdf.model.enums.countries import Country

MISSING = "xxx"
COUNTRIES = frozenset(Country.values())
TYPOLOGIES = frozenset(BuildingTypology.values())


def code_in(codes: frozenset[str], value: object) -> str:
    """The enum's 3-letter value: a member, or its value as stored. Anything else,
    a display name included, is not a code."""
    text = "" if value is None else str(value).strip().lower()
    return text if text in codes else MISSING


def country_code(value: object) -> str:
    return code_in(COUNTRIES, value)


def typology_code(value: object) -> str:
    return code_in(TYPOLOGIES, value)


def year_part(start: date | None, end: date | None) -> str:
    # A value that is not a date (a text the parser let through) counts as missing.
    year = getattr(start, "year", None) or getattr(end, "year", None)
    return MISSING if year is None else str(year)


def format_id(
    country: object,
    start: date | None,
    end: date | None,
    typology: object,
    number: int,
    version: int,
) -> str:
    return (
        f"{country_code(country)}_{year_part(start, end)}_{typology_code(typology)}"
        f"_{number:04d}_v{version}"
    )
