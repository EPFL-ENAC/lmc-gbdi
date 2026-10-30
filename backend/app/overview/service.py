"""The "Building carbon overview" sheet of the OpenBDF v2 workbook, formula for formula.

Each Bill of Materials row counts floor_repetition times. A stage sums the Wide GWP
modules of every row; a missing A1–A3 total falls back to A1+A2+A3, a missing A5 to
A5.1–A5.4. Shares divide by the whole-life total (A to C), so module D stays outside.
"""

import csv
from collections import defaultdict
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from app.overview.repo import MaterialPair, MaterialRow, ProjectData, read_project
from app.overview.schemas import (
    DataTypeShare,
    ElementStages,
    ElementTotal,
    Headline,
    MassHotspot,
    MaterialHotspot,
    ModuleCheck,
    Overview,
    ProjectField,
    ProjectInfo,
    StageTotal,
)

ZERO = Decimal(0)
STAGES = (
    ("a1_a3", "A1–A3"),
    ("a4_a5", "A4–A5"),
    ("b1_b8", "B1–B8"),
    ("c1_c4", "C1–C4"),
)
TOP_ELEMENTS = 8
TOP_MATERIALS = 10
# The seven construction product data types of Regulation (EU) 2026/52.
DATA_TYPES = (
    ("cpr_dopc", "Construction Products Regulation data"),
    ("ecodesign", "Ecodesign and energy labelling data"),
    ("project_specific", "Project-specific data"),
    ("product_specific", "Product-specific data"),
    ("product_group_average", "Average data for a product group"),
    ("generic", "Generic data"),
    ("default_value", "Default values"),
)

# The Project table of the sheet: (group, field code, label), in the sheet's order.
PROJECT_FIELDS = (
    ("Project", "project_id", "Project ID"),
    ("Project", "project_name", "Project name"),
    ("Project", "project_country", "Country"),
    ("Project", "project_no_of_buildings", "No. of buildings"),
    ("Project", "project_assessment_type", "Assessment type"),
    ("Project", "project_phase_common", "Project phase, common definition"),
    ("Building", "building_use_type", "Building typology"),
    ("Building", "building_structure_type", "Building structure type"),
    ("Building", "building_gross_floor_area", "Gross floor area (m²)"),
    ("Building", "building_useful_floor_area", "Useful floor area (m²)"),
    ("Building", "building_gross_floor_area_standard", "GFA standard"),
    ("Building", "building_element_classification_code_name", "Element classification"),
    ("Building", "lca_material_source", "Material quantities source"),
    ("Life cycle assessment", "lca_cycle_system_boundary", "System boundary"),
    ("Life cycle assessment", "lca_reference_study_period", "Study period (years)"),
    ("Life cycle assessment", "lcia_methodology", "LCIA methodology"),
    ("Life cycle assessment", "lca_database_name", "LCA database"),
    ("Life cycle assessment", "lca_database_version", "LCA database version"),
    ("Life cycle assessment", "lca_biogenic_method", "Biogenic carbon accounting"),
    ("Life cycle assessment", "lca_temporal_approach", "Temporal approach"),
    ("Life cycle assessment", "lca_lci_modeling_approach", "LCI modelling approach"),
    ("Life cycle assessment", "lca_third_party_verified", "Third-party verified"),
)
# Module scope flags of General Information and their Wide result column.
MODULES = (
    ("A1–A3", "lca_a1_3", "gwp_total_a1_a3"),
    *(
        (m.upper(), f"lca_{m}", f"gwp_total_{m}")
        for m in ("a1", "a2", "a3", "a4", "a5")
    ),
    *((f"A5.{i}", f"lca_a5_{i}", f"gwp_total_a5_{i}") for i in range(1, 5)),
    *((f"B{i}", f"lca_b{i}", f"gwp_total_b{i}") for i in range(1, 9)),
    *((f"C{i}", f"lca_c{i}", f"gwp_total_c{i}") for i in range(1, 5)),
)

with (Path(__file__).parent / "bec_tier2.csv").open(encoding="utf-8") as f:
    BEC_TIER2 = [(row["code"], row["name"]) for row in csv.DictReader(f)]

Stages = dict[str, Decimal]


def module(row: MaterialRow, field: str) -> Decimal:
    return row.gwp[field] or ZERO


def with_fallback(row: MaterialRow, total: str, parts: tuple[str, ...]) -> Decimal:
    value = row.gwp[total]
    return value if value is not None else sum((module(row, p) for p in parts), ZERO)


def stage_gwp(row: MaterialRow) -> Stages:
    a5 = ("gwp_total_a5_1", "gwp_total_a5_2", "gwp_total_a5_3", "gwp_total_a5_4")
    stages = {
        "a1_a3": with_fallback(
            row, "gwp_total_a1_a3", ("gwp_total_a1", "gwp_total_a2", "gwp_total_a3")
        ),
        "a4_a5": module(row, "gwp_total_a4") + with_fallback(row, "gwp_total_a5", a5),
        "b1_b8": sum((module(row, f"gwp_total_b{i}") for i in range(1, 9)), ZERO),
        "c1_c4": sum((module(row, f"gwp_total_c{i}") for i in range(1, 5)), ZERO),
    }
    return {key: value * row.repetition for key, value in stages.items()}


def add(total: Stages, part: Stages) -> Stages:
    return {key: total[key] + part[key] for key in total}


def in_element(row_element: str, code: str) -> bool:
    """Match by code: '2.1' takes '2.1', '2.1.3' and '2.1 Frame', never '2.10'."""
    return row_element == code or row_element.startswith((f"{code}.", f"{code} "))


def element_rollup(rows: list[tuple[MaterialRow, Stages]]) -> list[tuple[str, Stages]]:
    """Stage totals of every Tier 2 element that carries GWP, in OpenBDF order."""
    rollup = []
    for code, name in BEC_TIER2:
        totals = {key: ZERO for key, _ in STAGES}
        for row, stages in rows:
            if in_element(row.element, code):
                totals = add(totals, stages)
        if sum(totals.values()) != ZERO:
            rollup.append((name, totals))
    return rollup


def element_stages(name: str, stages: Stages) -> ElementStages:
    total = sum(stages.values(), ZERO)
    key, label = max(STAGES, key=lambda stage: stages[stage[0]])
    return ElementStages(
        element=name,
        gwp_by_stage={k: float(v) for k, v in stages.items()},
        dominant_stage=label,
        dominant_share=float(stages[key] / total),
    )


def material_rollup(
    rows: list[tuple[MaterialRow, Stages]],
) -> dict[MaterialPair, Stages]:
    """Whole-life GWP, mass and GWP fossil A1–A3 of each material + EPD product."""
    pairs: dict[MaterialPair, Stages] = defaultdict(
        lambda: {"gwp": ZERO, "mass": ZERO, "fossil": ZERO}
    )
    fossil_parts = ("gwp_f_a1", "gwp_f_a2", "gwp_f_a3")
    for row, stages in rows:
        pair = pairs[row.pair]
        pair["gwp"] += sum(stages.values(), ZERO)
        pair["mass"] += row.mass_kg * row.repetition
        pair["fossil"] += (
            with_fallback(row, "gwp_f_a1_a3", fossil_parts) * row.repetition
        )
    return pairs


def hotspots(
    pairs: dict[MaterialPair, Stages], whole_life: Decimal
) -> tuple[list[MaterialHotspot], list[MassHotspot]]:
    by_gwp = sorted(pairs.items(), key=lambda item: item[1]["gwp"], reverse=True)
    by_mass = sorted(pairs.items(), key=lambda item: item[1]["mass"], reverse=True)
    total_mass = sum((p["mass"] for p in pairs.values()), ZERO)
    gwp = [
        MaterialHotspot(
            material=material,
            epd_product=epd,
            gwp=float(p["gwp"]),
            mass_kg=float(p["mass"]),
            share=float(p["gwp"] / whole_life),
            gwp_per_kg=float(p["gwp"] / p["mass"]) if p["mass"] else None,
        )
        for (material, epd), p in by_gwp
        if round(p["gwp"]) != 0
    ]
    mass = [
        MassHotspot(
            material=material,
            epd_product=epd,
            mass_kg=float(p["mass"]),
            share_of_mass=float(p["mass"] / total_mass),
        )
        for (material, epd), p in by_mass
        if round(p["mass"]) != 0
    ]
    return gwp[:TOP_MATERIALS], mass[:TOP_MATERIALS]


def data_type_key(declared: str) -> str:
    """'Product specific (assessment …)' → 'product_specific', as the workbook does."""
    return declared.split(" (")[0].strip().lower().replace(" ", "_")


def data_type_profile(
    pairs: dict[MaterialPair, Stages], declared: dict[MaterialPair, str]
) -> tuple[str, list[DataTypeShare]]:
    weighting = "not_computed"
    if sum((p["mass"] for p in pairs.values()), ZERO) > ZERO:
        weighting = "mass"
    if sum((p["fossil"] for p in pairs.values()), ZERO) > ZERO:
        weighting = "gwp_fossil_a1_a3"
    if weighting == "not_computed":
        return weighting, []

    weight_field = "fossil" if weighting == "gwp_fossil_a1_a3" else "mass"
    total = sum((p[weight_field] for p in pairs.values()), ZERO)
    by_type: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for pair, p in pairs.items():
        # A pair with no Project material database line declares no data type.
        by_type[data_type_key(declared.get(pair, ""))] += p[weight_field]
    shares = [
        DataTypeShare(key=key, label=label, share=float(by_type[key] / total))
        for key, label in DATA_TYPES
    ]
    undeclared = 1 - sum(share.share for share in shares)
    return weighting, [
        *shares,
        DataTypeShare(key="undeclared", label="Undeclared", share=undeclared),
    ]


def text(general: dict[str, str], field: str) -> str | None:
    return general.get(field, "").strip() or None


def quantity(general: dict[str, str], field: str) -> Decimal | None:
    value = text(general, field)
    return None if value is None else Decimal(value)


def per(value: Decimal, *divisors: Decimal | None) -> float | None:
    if any(d is None or d == ZERO for d in divisors):
        return None
    result = value
    for divisor in divisors:
        result /= divisor
    return float(result)


def project_info(general: dict[str, str]) -> ProjectInfo:
    def number(field: str) -> float | None:
        value = quantity(general, field)
        return None if value is None else float(value)

    return ProjectInfo(
        project_id=text(general, "project_id"),
        project_name=text(general, "project_name"),
        country=text(general, "project_country"),
        gross_floor_area_m2=number("building_gross_floor_area"),
        useful_floor_area_m2=number("building_useful_floor_area"),
        reference_study_period_years=number("lca_reference_study_period"),
        lca_database=text(general, "lca_database_version")
        or text(general, "lca_database_name"),
        lcia_methodology=text(general, "lcia_methodology"),
        system_boundary=text(general, "lca_cycle_system_boundary"),
    )


def headline(data: ProjectData, totals: Stages) -> Headline:
    whole_life = sum(totals.values(), ZERO)
    useful = quantity(data.general, "building_useful_floor_area")
    gross = quantity(data.general, "building_gross_floor_area")
    period = quantity(data.general, "lca_reference_study_period")
    module_d = {
        field: sum((module(row, field) * row.repetition for row in data.rows), ZERO)
        for field in ("gwp_total_d1", "gwp_total_d2")
    }
    return Headline(
        whole_life=float(whole_life),
        upfront=float(totals["a1_a3"] + totals["a4_a5"]),
        per_m2_useful=per(whole_life, useful),
        per_m2_gross=per(whole_life, gross),
        per_m2_useful_per_year=per(whole_life, useful, period),
        module_d1=float(module_d["gwp_total_d1"]),
        module_d2=float(module_d["gwp_total_d2"]),
    )


def project_fields(general: dict[str, str]) -> list[ProjectField]:
    return [
        ProjectField(code=code, label=label, group=group, value=text(general, code))
        for group, code, label in PROJECT_FIELDS
    ]


def declared(general: dict[str, str], flag: str) -> bool:
    """The workbook's N(x)=1 or UPPER(x)="TRUE"."""
    value = (text(general, flag) or "").upper()
    return value in ("TRUE", "1")


def module_checks(data: ProjectData) -> list[ModuleCheck]:
    """Declared modules against the results present: a plain sum of the Wide column."""
    checks = []
    for module_name, flag, field in MODULES:
        total = sum((row.gwp[field] or ZERO for row in data.rows), ZERO)
        has_result = round(total, 6) != ZERO
        is_declared = declared(data.general, flag)
        status = "ok"
        if is_declared and not has_result:
            status = "declared_no_result"
        if has_result and not is_declared:
            status = "result_not_declared"
        checks.append(
            ModuleCheck(
                module=module_name,
                declared=is_declared,
                has_result=has_result,
                status=status,
            )
        )
    return checks


def bucket(name: str, gwp: Decimal, whole_life: Decimal) -> ElementTotal:
    return ElementTotal(element=name, gwp=float(gwp), share=float(gwp / whole_life))


def build_overview(data: ProjectData) -> Overview:
    rows = [(row, stage_gwp(row)) for row in data.rows]
    totals = {key: sum((stages[key] for _, stages in rows), ZERO) for key, _ in STAGES}
    whole_life = sum(totals.values(), ZERO)
    if whole_life == ZERO:
        raise ValueError("The project's whole-life GWP is zero: nothing to share out")

    elements = element_rollup(rows)
    classified = sum((sum(s.values(), ZERO) for _, s in elements), ZERO)
    shown = elements[:TOP_ELEMENTS]
    shown_total = sum((sum(s.values(), ZERO) for _, s in shown), ZERO)
    pairs = material_rollup(rows)
    material_hotspots, mass_hotspots = hotspots(pairs, whole_life)
    weighting, data_types = data_type_profile(pairs, data.data_types)
    checks = module_checks(data)
    return Overview(
        project=project_info(data.general),
        project_fields=project_fields(data.general),
        rows_read=len(data.rows),
        module_checks=checks,
        modules_declared_without_result=sum(
            c.status == "declared_no_result" for c in checks
        ),
        modules_with_undeclared_result=sum(
            c.status == "result_not_declared" for c in checks
        ),
        headline=headline(data, totals),
        stages=[
            StageTotal(
                key=k,
                label=label,
                gwp=float(totals[k]),
                share=float(totals[k] / whole_life),
            )
            for k, label in STAGES
        ],
        elements=[
            ElementTotal(
                element=name,
                gwp=float(t := sum(s.values(), ZERO)),
                share=float(t / whole_life),
            )
            for name, s in shown
        ],
        other_classified=bucket(
            "Other classified elements", classified - shown_total, whole_life
        ),
        not_classified=bucket("Not classified", whole_life - classified, whole_life),
        element_stages=[element_stages(name, s) for name, s in shown],
        material_hotspots=material_hotspots,
        mass_hotspots=mass_hotspots,
        data_type_weighting=weighting,
        data_types=data_types,
    )


@lru_cache(maxsize=1)
def project_overview(data_dir: Path) -> Overview:
    """Read and compute once per process: the CSVs only change with a redeploy."""
    return build_overview(read_project(data_dir))
