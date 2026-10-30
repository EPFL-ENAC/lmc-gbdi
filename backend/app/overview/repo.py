"""Read one OpenBDF project from its CSV export (scripts/openbdf_xlsx_to_csv.py).

File-backed on purpose: there are no project tables until uploads exist. Once the
lmc-openbdf parser reads v2 workbooks, its ProjectRecord replaces this reader; the
field codes are the same.
"""

import csv
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

# Wide LCA result fields the overview reads: GWP total per module, GWP fossil A1–A3.
GWP_FIELDS = (
    "gwp_total_a1_a3", "gwp_total_a1", "gwp_total_a2", "gwp_total_a3",
    "gwp_total_a4", "gwp_total_a5",
    "gwp_total_a5_1", "gwp_total_a5_2", "gwp_total_a5_3", "gwp_total_a5_4",
    "gwp_total_b1", "gwp_total_b2", "gwp_total_b3", "gwp_total_b4",
    "gwp_total_b5", "gwp_total_b6", "gwp_total_b7", "gwp_total_b8",
    "gwp_total_c1", "gwp_total_c2", "gwp_total_c3", "gwp_total_c4",
    "gwp_total_d1", "gwp_total_d2",
    "gwp_f_a1_a3", "gwp_f_a1", "gwp_f_a2", "gwp_f_a3",
)  # fmt: skip
BOM_FIELDS = (
    "material_id",
    "floor_repetition",
    "bec_openbdf",
    "custom_material_name",
    "lca_dataset_material_name",
    "material_weight_kg",
)
PMD_FIELDS = ("custom_material_name", "lca_dataset_material_name", "material_data_type")

MaterialPair = tuple[str, str]  # (custom_material_name, lca_dataset_material_name)


@dataclass(frozen=True)
class MaterialRow:
    """One Bill of Materials row joined with its Wide LCA results."""

    material_id: str
    element: str  # bec_openbdf; "" when the row is not classified
    pair: MaterialPair
    repetition: Decimal  # floor_repetition; blank or 0 counts once, as in the workbook
    mass_kg: Decimal
    gwp: dict[str, Decimal | None]  # None = blank cell, which drives the fallbacks
    # OpenBDF material class, "4.2 Concrete"; the CSV export has no such column.
    material_class: str = ""


@dataclass(frozen=True)
class ProjectData:
    general: dict[str, str]
    rows: list[MaterialRow]
    data_types: dict[MaterialPair, str]  # from the Project material database


def read_csv(path: Path, required: tuple[str, ...]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = set(required) - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"{path.name} lacks the columns {sorted(missing)}")
        return list(reader)


def number(text: str) -> Decimal | None:
    return Decimal(text) if text.strip() else None


def by_material_id(
    rows: list[dict[str, str]], source: str
) -> dict[str, dict[str, str]]:
    keyed: dict[str, dict[str, str]] = {}
    for row in rows:
        if row["material_id"] in keyed:
            raise ValueError(
                f"{source}: material_id {row['material_id']!r} appears twice"
            )
        keyed[row["material_id"]] = row
    return keyed


def join_row(bom: dict[str, str], wide: dict[str, str]) -> MaterialRow:
    repetition = number(bom["floor_repetition"]) or Decimal(1)
    return MaterialRow(
        material_id=bom["material_id"],
        element=bom["bec_openbdf"].strip(),
        pair=(
            bom["custom_material_name"].strip(),
            bom["lca_dataset_material_name"].strip(),
        ),
        repetition=repetition,
        mass_kg=number(bom["material_weight_kg"]) or Decimal(0),
        gwp={field: number(wide[field]) for field in GWP_FIELDS},
    )


def read_project(data_dir: Path) -> ProjectData:
    bom = by_material_id(
        read_csv(data_dir / "bill_of_materials.csv", BOM_FIELDS), "Bill of Materials"
    )
    wide = by_material_id(
        read_csv(data_dir / "lca_results_wide.csv", ("material_id", *GWP_FIELDS)),
        "LCA Result (Wide)",
    )
    if bom.keys() != wide.keys():
        unmatched = sorted(bom.keys() ^ wide.keys())[:5]
        raise ValueError(
            f"Bill of Materials and Wide results disagree on material_id: {unmatched}"
        )

    general = {
        row["field_code"]: row["value"]
        for row in read_csv(
            data_dir / "general_information.csv", ("field_code", "value")
        )
    }
    data_types = {
        (
            row["custom_material_name"].strip(),
            row["lca_dataset_material_name"].strip(),
        ): row["material_data_type"].strip()
        for row in read_csv(data_dir / "project_material_database.csv", PMD_FIELDS)
    }
    rows = [join_row(bom[material_id], wide[material_id]) for material_id in bom]
    return ProjectData(general=general, rows=rows, data_types=data_types)
