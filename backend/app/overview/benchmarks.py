"""Published reference scales to place a project on, with their scope stated.

Reference points, not compliance checks: each scale counts its own modules over its
own floor area, so the comparison is indicative and the scope note says how.
"""

from app.overview.schemas import Benchmark, BenchmarkBand, Headline

# (key, name, source, url, scope, which figure is compared, bands)
# Bands ascend and include their upper bound; the last one is open-ended (upper None).
SCALES = (
    (
        "re2020",
        "RE2020 ceiling on Ic construction, collective housing (France)",
        "RE2020 thresholds by building permit year, as published for 2022 to 2031",
        "https://projetcelsius.com/en/blog/re2020-2028-thresholds/",
        "RE2020 uses a dynamic LCA over 50 years and its own reference area. This "
        "project is a static LCA, placed by its whole life per m² of useful floor "
        "area. Indicative only.",
        "per_m2_useful",
        (
            ("Within the 2031 ceiling", 490),
            ("Within the 2028 ceiling", 580),
            ("Within the 2025 ceiling", 650),
            ("Within the 2022 ceiling", 740),
            ("Above the 2022 ceiling", None),
        ),
    ),
)  # fmt: skip


def band_of(value: float, bands: tuple) -> str:
    for label, upper in bands:
        if upper is None or value <= upper:
            return label
    raise ValueError("A scale's last band must be open-ended")


def benchmarks(headline: Headline) -> list[Benchmark]:
    result = []
    for key, name, source, url, scope, basis, bands in SCALES:
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
                band=None if value is None else band_of(value, bands),
            )
        )
    return result
