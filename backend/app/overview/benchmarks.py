"""Published reference scales to place a project on, with their scope stated.

Reference points, not compliance checks: each scale counts its own modules over its
own floor area, so the comparison is indicative and the scope note says how.
"""

from app.overview.schemas import Benchmark, BenchmarkBand, Headline

# (key, name, source, url, scope, which figure is compared, inclusive, bands)
# Bands ascend; the last one is open-ended (upper None).
SCALES = (
    (
        "leti",
        "LETI embodied carbon rating, residential",
        "LETI Embodied Carbon Primer, bands as listed by the RICS Built Environment "
        "Journal",
        "https://ww3.rics.org/uk/en/journals/built-environment-journal/"
        "reducing-embodied-carbon-in-building-materials.html",
        "LETI rates modules A1–A5, B1–B5 and C1–C4 per m² of gross internal area. "
        "This project is placed by its whole life (A to C) per m² of gross floor area, "
        "which includes the walls, so it reads lower than per internal area would.",
        "per_m2_gross",
        False,
        (
            ("A++", 100), ("A+", 200), ("A", 300), ("B", 400), ("C", 500),
            ("D", 675), ("E", 850), ("F", 1000), ("G", 1200), ("Beyond G", None),
        ),
    ),
    (
        "re2020",
        "RE2020 ceiling on Ic construction, collective housing (France)",
        "RE2020 thresholds by building permit year, as published for 2022 to 2031",
        "https://projetcelsius.com/en/blog/re2020-2028-thresholds/",
        "RE2020 uses a dynamic LCA over 50 years and its own reference area. This "
        "project is a static LCA, placed by its whole life per m² of useful floor "
        "area. Indicative only.",
        "per_m2_useful",
        True,
        (
            ("Within the 2031 ceiling", 490),
            ("Within the 2028 ceiling", 580),
            ("Within the 2025 ceiling", 650),
            ("Within the 2022 ceiling", 740),
            ("Above the 2022 ceiling", None),
        ),
    ),
)  # fmt: skip


def band_of(value: float, bands: tuple, inclusive: bool) -> str:
    for label, upper in bands:
        if upper is None or value < upper or (inclusive and value == upper):
            return label
    raise ValueError("A scale's last band must be open-ended")


def benchmarks(headline: Headline) -> list[Benchmark]:
    result = []
    for key, name, source, url, scope, basis, inclusive, bands in SCALES:
        value = getattr(headline, basis)
        result.append(
            Benchmark(
                key=key,
                name=name,
                source=source,
                source_url=url,
                scope=scope,
                basis=basis,
                value=value,
                bands=[BenchmarkBand(label=label, upper=up) for label, up in bands],
                band=None if value is None else band_of(value, bands, inclusive),
            )
        )
    return result
