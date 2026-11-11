"""The "Building carbon overview" sheet of the OpenBDF v2 workbook, formula for formula.

Each Bill of Materials row counts floor_repetition times. A stage sums the Wide GWP
modules of every row; a missing A1–A3 total falls back to A1+A2+A3, a missing A5 to
A5.1–A5.4. Shares divide by the whole-life total (A to C), so module D stays outside.
"""

import csv
import re
from collections import defaultdict
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from app.overview.repo import MaterialPair, MaterialRow, ProjectData, read_project
from app.overview.schemas import (
    Basis,
    BasisOption,
    DataTypeShare,
    ElementMaterial,
    ElementMaterials,
    ElementStages,
    ElementTotal,
    Headline,
    MassHotspot,
    MaterialClassTotal,
    MaterialHotspot,
    ModuleCheck,
    Naming,
    NamingView,
    Overview,
    ProjectField,
    ProjectInfo,
    StageTotal,
    TimeFigures,
    Units,
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
TOP_ELEMENT_MATERIALS = 5
NAMINGS: tuple[Naming, ...] = ("openbdf", "custom")
OTHER_CLASSIFIED = "Other classified elements"
NOT_CLASSIFIED = "Not classified"
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
    ("Project", "project_city", "City"),
    ("Project", "project_address", "Address"),
    ("Project", "project_architect_engineer_name", "Architect or engineer"),
    ("Project", "project_construction_type", "Construction type"),
    ("Project", "project_no_of_buildings", "No. of buildings"),
    ("Project", "project_assessment_type", "Assessment type"),
    ("Project", "project_phase_common", "Project phase, common definition"),
    ("Building", "building_use_type", "Building typology"),
    ("Building", "building_structure_type", "Building structure type"),
    ("Building", "building_residential_units", "Residential units"),
    ("Building", "building_construction_start_date", "Construction start"),
    ("Building", "building_construction_end_date", "Construction end"),
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
# The Overview's title block, in the order of globalbuildingdatainitiative/org#97: what
# the project is, then the five attributes that decide whether two results compare.
TITLE_BLOCK = (
    "project_id",
    "project_country",
    "building_use_type",
    "building_structure_type",
    "building_gross_floor_area",
    "building_gross_floor_area_standard",
    "lca_reference_study_period",
    "project_assessment_type",
    "project_phase_common",
    "lca_cycle_system_boundary",
    "lcia_methodology",
    "lca_biogenic_method",
    "lca_temporal_approach",
    "lca_lci_modeling_approach",
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
TIER2_ORDER = {name: i for i, (_, name) in enumerate(BEC_TIER2)}

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


def element_label(row: MaterialRow, naming: Naming) -> str:
    """The element a row counts in: its Tier 2 element, or its bec_custom class.

    "" when the row is not classified under the naming. The custom element is
    bec_custom, the counterpart the OpenBDF translator derives bec_openbdf from;
    custom_element_name names one element and, on AT-09, repeats the material.
    """
    if naming == "custom":
        return row.element_custom
    return next((name for code, name in BEC_TIER2 if in_element(row.element, code)), "")


def material_key(row: MaterialRow, naming: Naming) -> MaterialPair:
    """The material a row counts in: its custom name and EPD product, or its class."""
    if naming == "custom":
        return row.pair
    return (row.material_class or NOT_CLASSIFIED, "")


def element_rollup(
    rows: list[tuple[MaterialRow, Stages]], naming: Naming = "openbdf"
) -> list[tuple[str, Stages, Decimal]]:
    """Stage totals and mass of every element that carries GWP or mass.

    OpenBDF elements come in classification order; custom classes by label, which
    their codes lead ("2D.01 …", "2E.01 …").
    """
    groups: dict[str, tuple[Stages, list[Decimal]]] = defaultdict(
        lambda: ({key: ZERO for key, _ in STAGES}, [ZERO])
    )
    for row, stages in rows:
        if label := element_label(row, naming):
            totals, mass = groups[label]
            for key, value in stages.items():
                totals[key] += value
            mass[0] += row.mass_kg * row.repetition
    rollup = [
        (name, totals, mass)
        for name, (totals, [mass]) in groups.items()
        if sum(totals.values(), ZERO) != ZERO or mass != ZERO
    ]
    if naming == "openbdf":
        return sorted(rollup, key=lambda item: TIER2_ORDER[item[0]])
    return sorted(rollup, key=lambda item: item[0])


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
    rows: list[tuple[MaterialRow, Stages]], naming: Naming = "custom"
) -> dict[MaterialPair, Stages]:
    """Whole-life GWP, mass and GWP fossil A1–A3 of each material + EPD product, or
    of each OpenBDF material class."""
    pairs: dict[MaterialPair, Stages] = defaultdict(
        lambda: (
            {"gwp": ZERO, "mass": ZERO, "fossil": ZERO} | {k: ZERO for k, _ in STAGES}
        )
    )
    fossil_parts = ("gwp_f_a1", "gwp_f_a2", "gwp_f_a3")
    for row, stages in rows:
        pair = pairs[material_key(row, naming)]
        pair["gwp"] += sum(stages.values(), ZERO)
        for key, value in stages.items():
            pair[key] += value
        pair["mass"] += row.mass_kg * row.repetition
        pair["fossil"] += (
            with_fallback(row, "gwp_f_a1_a3", fossil_parts) * row.repetition
        )
    return pairs


def hotspots(
    pairs: dict[MaterialPair, Stages], whole_life: Decimal
) -> tuple[list[MaterialHotspot], list[MassHotspot], Decimal, list[MaterialHotspot]]:
    by_gwp = sorted(pairs.items(), key=lambda item: item[1]["gwp"], reverse=True)
    by_mass = sorted(pairs.items(), key=lambda item: item[1]["mass"], reverse=True)
    total_mass = sum((p["mass"] for p in pairs.values()), ZERO)
    every = [
        MaterialHotspot(
            material=material,
            epd_product=epd,
            gwp=float(p["gwp"]),
            mass_kg=float(p["mass"]),
            share=float(p["gwp"] / whole_life),
            share_of_mass=float(p["mass"] / total_mass) if total_mass else None,
            gwp_per_kg=float(p["gwp"] / p["mass"]) if p["mass"] else None,
            gwp_by_stage={k: float(p[k]) for k, _ in STAGES},
        )
        for (material, epd), p in by_gwp
        if round(p["gwp"]) != 0 or round(p["mass"]) != 0
    ]
    mass = [
        MassHotspot(
            material=material,
            epd_product=epd,
            mass_kg=float(p["mass"]),
            share_of_mass=float(p["mass"] / total_mass),
            gwp=float(p["gwp"]),
            share=float(p["gwp"] / whole_life),
        )
        for (material, epd), p in by_mass
        if round(p["mass"]) != 0
    ]
    top_mass = sum((p["mass"] for _, p in by_mass[:TOP_MATERIALS]), ZERO)
    other_share = (total_mass - top_mass) / total_mass if total_mass else ZERO
    # The carbon top 10 needs carbon; `every` keeps the mass-only materials too.
    top_gwp = [h for h in every if round(h.gwp) != 0][:TOP_MATERIALS]
    return top_gwp, mass[:TOP_MATERIALS], other_share, every


def class_rollup(rows: list[tuple[MaterialRow, Stages]]) -> list[MaterialClassTotal]:
    """Whole-life GWP and mass by OpenBDF material class: the names that compare
    across projects, where custom material names never match."""
    classes: dict[str, Stages] = defaultdict(lambda: {"gwp": ZERO, "mass": ZERO})
    for row, stages in rows:
        totals = classes[row.material_class or NOT_CLASSIFIED]
        totals["gwp"] += sum(stages.values(), ZERO)
        totals["mass"] += row.mass_kg * row.repetition
    return [
        MaterialClassTotal(label=label, gwp=float(t["gwp"]), mass_kg=float(t["mass"]))
        for label, t in sorted(classes.items())
    ]


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


# The OpenBDF converter fills a blank project ID with this placeholder.
PLACEHOLDER_ID = re.compile(r"X+", re.IGNORECASE)


def text(general: dict[str, str], field: str) -> str | None:
    value = general.get(field, "").strip() or None
    if field == "project_id" and value and PLACEHOLDER_ID.fullmatch(value):
        return None
    return value


def quantity(general: dict[str, str], field: str) -> Decimal | None:
    value = text(general, field)
    return None if value is None else Decimal(value)


# OpenBDF types the study period as text: "50", "60 years". A number of years,
# optionally a year word; anything else is refused, never read as "not declared".
STUDY_PERIOD = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:years?|yrs?|y)?", re.IGNORECASE)


def study_period(general: dict[str, str]) -> Decimal | None:
    value = text(general, "lca_reference_study_period")
    if value is None:
        return None
    match = STUDY_PERIOD.fullmatch(value)
    if match is None:
        raise ValueError(f"the study period {value!r} is not a number of years")
    return Decimal(match.group(1).replace(",", "."))


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
        reference_study_period_years=None
        if (years := study_period(general)) is None
        else float(years),
        lca_database=text(general, "lca_database_version")
        or text(general, "lca_database_name"),
        lcia_methodology=text(general, "lcia_methodology"),
        system_boundary=text(general, "lca_cycle_system_boundary"),
    )


def headline(data: ProjectData, totals: Stages) -> Headline:
    whole_life = sum(totals.values(), ZERO)
    useful = quantity(data.general, "building_useful_floor_area")
    gross = quantity(data.general, "building_gross_floor_area")
    period = study_period(data.general)
    module_d = {
        field: sum((module(row, field) * row.repetition for row in data.rows), ZERO)
        for field in ("gwp_total_d1", "gwp_total_d2")
    }
    return Headline(
        whole_life=float(whole_life),
        upfront=float(totals["a1_a3"] + totals["a4_a5"]),
        upfront_share=float((totals["a1_a3"] + totals["a4_a5"]) / whole_life),
        per_m2_useful=per(whole_life, useful),
        per_m2_gross=per(whole_life, gross),
        per_m2_useful_per_year=per(whole_life, useful, period),
        per_m2_gross_per_year=per(whole_life, gross, period),
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


def bucket(
    name: str, gwp: Decimal, mass: Decimal, whole_life: Decimal, total_mass: Decimal
) -> ElementTotal:
    return ElementTotal(
        element=name,
        gwp=float(gwp),
        share=float(gwp / whole_life),
        mass_kg=float(mass),
        share_of_mass=float(mass / total_mass) if total_mass else None,
    )


def element_materials(
    rows: list[tuple[MaterialRow, Stages]], naming: Naming, shown: list[str]
) -> list[ElementMaterials]:
    """The mass of each material within each element bar: the shown elements, then
    the other classified ones together, then the rows not classified."""
    # The two buckets are kept apart from the shown bars: a project can name one of
    # its own elements "Not classified".
    bars: list[tuple[str, dict[MaterialPair, Decimal]]] = [
        (name, defaultdict(lambda: ZERO))
        for name in (*shown, OTHER_CLASSIFIED, NOT_CLASSIFIED)
    ]
    by_label = dict(bars[: len(shown)])
    other, unclassified = bars[-2][1], bars[-1][1]
    for row, _ in rows:
        label = element_label(row, naming)
        bar = by_label.get(label, other) if label else unclassified
        bar[material_key(row, naming)] += row.mass_kg * row.repetition

    def part(material: MaterialPair, mass: Decimal, total: Decimal) -> ElementMaterial:
        return ElementMaterial(
            material=material[0],
            epd_product=material[1],
            mass_kg=float(mass),
            share=float(mass / total) if total else None,
        )

    result = []
    for i, (name, masses) in enumerate(bars):
        total = sum(masses.values(), ZERO)
        if i >= len(shown) and total == ZERO:
            continue  # an empty bucket would open onto nothing
        heaviest = sorted(
            ((m, kg) for m, kg in masses.items() if kg != ZERO),
            key=lambda item: item[1],
            reverse=True,
        )
        # One material left over is shown, not folded into "1 other materials".
        cut = (
            TOP_ELEMENT_MATERIALS if len(heaviest) > TOP_ELEMENT_MATERIALS + 1 else None
        )
        top, rest = heaviest[:cut], heaviest[cut:] if cut else []
        others = sum((kg for _, kg in rest), ZERO)
        result.append(
            ElementMaterials(
                element=name,
                mass_kg=float(total),
                materials=[part(m, kg, total) for m, kg in top],
                other=part((f"{len(rest)} other materials", ""), others, total)
                if rest
                else None,
            )
        )
    return result


def naming_view(
    rows: list[tuple[MaterialRow, Stages]],
    naming: Naming,
    whole_life: Decimal,
    total_mass: Decimal,
) -> NamingView:
    """Every element and material figure under one naming. The element bars add up
    to the whole-life GWP and to the total mass."""
    elements = element_rollup(rows, naming)
    # Elements that carry carbon take the bars first, in classification or label
    # order. A mass-only element gets a bar only when fewer than eight carry carbon,
    # so it never pushes a carbon element into "Other classified elements".
    # ponytail: order, not size, picks the eight, as before stage 4. The comparison
    # aligns two buildings by element name, and order keeps their sets alike.
    carbon = [e for e in elements if sum(e[1].values(), ZERO) != ZERO]
    mass_only = [e for e in elements if sum(e[1].values(), ZERO) == ZERO]
    kept = {name for name, _, _ in (carbon + mass_only)[:TOP_ELEMENTS]}
    shown = [e for e in elements if e[0] in kept]

    def gwp(items: list[tuple[str, Stages, Decimal]]) -> Decimal:
        return sum((sum(s.values(), ZERO) for _, s, _ in items), ZERO)

    def mass(items: list[tuple[str, Stages, Decimal]]) -> Decimal:
        return sum((m for _, _, m in items), ZERO)

    material_hotspots, mass_hotspots, mass_other_share, materials = hotspots(
        material_rollup(rows, naming), whole_life
    )
    return NamingView(
        elements=[
            bucket(name, sum(s.values(), ZERO), m, whole_life, total_mass)
            for name, s, m in shown
        ],
        other_classified=bucket(
            OTHER_CLASSIFIED,
            gwp(elements) - gwp(shown),
            mass(elements) - mass(shown),
            whole_life,
            total_mass,
        ),
        not_classified=bucket(
            NOT_CLASSIFIED,
            whole_life - gwp(elements),
            total_mass - mass(elements),
            whole_life,
            total_mass,
        ),
        # The dominant stage divides by the element's carbon: mass-only ones skip.
        element_stages=[
            element_stages(name, s)
            for name, s, _ in shown
            if sum(s.values(), ZERO) != ZERO
        ],
        material_hotspots=material_hotspots,
        mass_hotspots=mass_hotspots,
        materials=materials,
        mass_other_share=float(mass_other_share),
        element_materials=element_materials(rows, naming, [n for n, _, _ in shown]),
    )


def from_views(namings: dict[Naming, NamingView]) -> dict:
    """The top-level fields the comparison and the building list read: OpenBDF
    elements and custom materials, as before the names toggle."""
    elements, materials = namings["openbdf"], namings["custom"]
    return {
        "elements": elements.elements,
        "other_classified": elements.other_classified,
        "not_classified": elements.not_classified,
        "element_stages": elements.element_stages,
        "material_hotspots": materials.material_hotspots,
        "mass_hotspots": materials.mass_hotspots,
        "materials": materials.materials,
        "mass_other_share": materials.mass_other_share,
        "namings": namings,
    }


def build_overview(data: ProjectData) -> Overview:
    rows = [(row, stage_gwp(row)) for row in data.rows]
    totals = {key: sum((stages[key] for _, stages in rows), ZERO) for key, _ in STAGES}
    whole_life = sum(totals.values(), ZERO)
    if whole_life == ZERO:
        raise ValueError("The project's whole-life GWP is zero: nothing to share out")

    total_mass = sum((row.mass_kg * row.repetition for row, _ in rows), ZERO)
    namings = {n: naming_view(rows, n, whole_life, total_mass) for n in NAMINGS}
    pairs = material_rollup(rows)
    period = study_period(data.general)
    summary = headline(data, totals)
    weighting, data_types = data_type_profile(pairs, data.data_types)
    checks = module_checks(data)
    fields = project_fields(data.general)
    by_code = {f.code: f for f in fields}
    project = project_info(data.general)
    stages = [
        StageTotal(
            key=k,
            label=label,
            gwp=float(totals[k]),
            share=float(totals[k] / whole_life),
        )
        for k, label in STAGES
    ]
    return Overview(
        project=project,
        project_fields=fields,
        title_block=[by_code[code] for code in TITLE_BLOCK],
        rows_read=len(data.rows),
        module_checks=checks,
        modules_declared_without_result=sum(
            c.status == "declared_no_result" for c in checks
        ),
        modules_with_undeclared_result=sum(
            c.status == "result_not_declared" for c in checks
        ),
        headline=summary,
        stages=stages,
        **from_views(namings),
        total_mass_kg=float(total_mass),
        material_classes=class_rollup(rows),
        time=TimeFigures(
            stages=stages,
            upfront=summary.upfront,
            use_per_year=per(totals["b1_b8"], period),
            module_d1=summary.module_d1,
        ),
        units=units("total"),
        bases=basis_options(project),
        data_type_weighting=weighting,
        data_types=data_types,
    )


# Each basis: its label, and what its carbon and its mass are per ("" for the total).
BASES: dict[Basis, tuple[str, str, str]] = {
    "total": ("Total", "", ""),
    "gfa": ("Per m² GFA", " per m² GFA", " per m² GFA"),
    "ufa": ("Per m² UFA", " per m² UFA", " per m² UFA"),
    "gfa_year": ("Per m² GFA and year", " per m² GFA and year", " per m² GFA"),
}


class BasisUnavailable(ValueError):
    """The building does not declare what the basis divides by."""


def units(basis: Basis) -> Units:
    _, carbon, area = BASES[basis]
    return Units(
        basis=basis,
        carbon=f"kg CO₂e{carbon}",
        mass=f"kg{area}",
        time=f"kg CO₂e{area}",
        intensity="kg CO₂e per kg and year"
        if basis == "gfa_year"
        else "kg CO₂e per kg",
    )


def missing(project: ProjectInfo, basis: Basis) -> str | None:
    """Why the building cannot serve the basis; None when it can."""
    needs = {
        "total": [],
        "gfa": [(project.gross_floor_area_m2, "gross floor area")],
        "ufa": [(project.useful_floor_area_m2, "useful floor area")],
        "gfa_year": [
            (project.gross_floor_area_m2, "gross floor area"),
            (project.reference_study_period_years, "study period"),
        ],
    }[basis]
    lacking = [name for value, name in needs if not value]
    return f"The workbook declares no {' and no '.join(lacking)}." if lacking else None


def basis_options(project: ProjectInfo) -> list[BasisOption]:
    return [
        BasisOption(
            key=key,
            label=label,
            available=(why := missing(project, key)) is None,
            reason=why,
        )
        for key, (label, _, _) in BASES.items()
    ]


def on_basis(o: Overview, basis: Basis) -> Overview:
    """The overview with every absolute figure divided by the basis; shares unchanged.

    Carbon is divided by the area, and by the study period under gfa_year; mass and
    the Time section's figures by the area only.
    """
    if why := missing(o.project, basis):
        raise BasisUnavailable(why)
    if basis == "total":
        return o
    p = o.project
    area = p.useful_floor_area_m2 if basis == "ufa" else p.gross_floor_area_m2
    years = p.reference_study_period_years if basis == "gfa_year" else 1.0
    assert area and years  # missing() has checked both
    # ponytail: divides the cached floats, not the workbook's Decimals, so the last
    # digit can differ from a full rebuild; rebuild per basis if that ever shows.
    c = area * years

    def stage(s: StageTotal, by: float) -> StageTotal:
        return s.model_copy(update={"gwp": s.gwp / by})

    h, t = o.headline, o.time
    namings = {n: view_on_basis(v, c, area) for n, v in o.namings.items()}
    return o.model_copy(
        update={
            "headline": h.model_copy(
                update={
                    "whole_life": h.whole_life / c,
                    "upfront": h.upfront / c,
                    "module_d1": h.module_d1 / c,
                    "module_d2": h.module_d2 / c,
                }
            ),
            "stages": [stage(s, c) for s in o.stages],
            **from_views(namings),
            "total_mass_kg": o.total_mass_kg / area,
            "material_classes": [
                m.model_copy(update={"gwp": m.gwp / c, "mass_kg": m.mass_kg / area})
                for m in o.material_classes
            ],
            "time": TimeFigures(
                stages=[stage(s, area) for s in t.stages],
                upfront=t.upfront / area,
                use_per_year=None if t.use_per_year is None else t.use_per_year / area,
                module_d1=t.module_d1 / area,
            ),
            "units": units(basis),
        }
    )


def view_on_basis(v: NamingView, c: float, area: float) -> NamingView:
    """A naming's figures with carbon divided by `c` and mass by `area`.

    model_copy skips a field it is not told about, so a figure added to the view
    needs a line here; test_overview_namings walks every field to catch one.
    """

    def stages(d: dict[str, float]) -> dict[str, float]:
        return {k: x / c for k, x in d.items()}

    def element(e: ElementTotal) -> ElementTotal:
        return e.model_copy(update={"gwp": e.gwp / c, "mass_kg": e.mass_kg / area})

    def hotspot(h: MaterialHotspot) -> MaterialHotspot:
        return h.model_copy(
            update={
                "gwp": h.gwp / c,
                "mass_kg": h.mass_kg / area,
                "gwp_by_stage": stages(h.gwp_by_stage),
            }
        )

    def part(m: ElementMaterial) -> ElementMaterial:
        return m.model_copy(update={"mass_kg": m.mass_kg / area})

    return v.model_copy(
        update={
            "elements": [element(e) for e in v.elements],
            "other_classified": element(v.other_classified),
            "not_classified": element(v.not_classified),
            "element_stages": [
                e.model_copy(update={"gwp_by_stage": stages(e.gwp_by_stage)})
                for e in v.element_stages
            ],
            "material_hotspots": [hotspot(m) for m in v.material_hotspots],
            "materials": [hotspot(m) for m in v.materials],
            "mass_hotspots": [
                m.model_copy(update={"gwp": m.gwp / c, "mass_kg": m.mass_kg / area})
                for m in v.mass_hotspots
            ],
            "element_materials": [
                e.model_copy(
                    update={
                        "mass_kg": e.mass_kg / area,
                        "materials": [part(m) for m in e.materials],
                        "other": None if e.other is None else part(e.other),
                    }
                )
                for e in v.element_materials
            ],
        }
    )


@lru_cache(maxsize=1)
def project_overview(data_dir: Path) -> Overview:
    """Read and compute once per process: the CSVs only change with a redeploy."""
    return build_overview(read_project(data_dir))
