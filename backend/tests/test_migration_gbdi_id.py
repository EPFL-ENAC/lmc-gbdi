"""The backfill of upload.gbdi_id, without a database: the migration's own assign."""

import importlib.util
from datetime import UTC, date, datetime
from pathlib import Path

from app.buildings.gbdi_id import format_id

PATH = Path(__file__).parents[1] / "alembic/versions/e3a91c5f2b07_upload_gbdi_id.py"
spec = importlib.util.spec_from_file_location("upload_gbdi_id", PATH)
assert spec is not None and spec.loader is not None
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


def at(day: int) -> datetime:
    return datetime(2026, 11, day, tzinfo=UTC)


# Shuffled; uploads 9 and 4 share a time, so the lower id goes first.
ROWS = [
    (9, at(3), "aut", None, date(2025, 6, 1), "sfh"),
    (2, at(5), None, date(2023, 1, 1), None, "off"),
    (7, at(1), "aut", date(2024, 3, 1), date(2026, 1, 15), "mfh"),
    (4, at(3), "aut", None, None, None),
]


def test_the_oldest_upload_takes_the_first_number_of_its_country():
    ids, counters = migration.assign(ROWS)
    assert [(i["id"], i["gbdi_id"]) for i in ids] == [
        (7, "aut_2024_mfh_0001_v1"),
        (4, "aut_xxx_xxx_0002_v1"),
        (9, "aut_2025_sfh_0003_v1"),
        (2, "xxx_2023_off_0001_v1"),
    ]
    assert counters == {"aut": 3, "xxx": 1}


def test_the_backfill_writes_the_ids_the_app_writes():
    ids, _ = migration.assign(ROWS)
    rows = {r[0]: r for r in ROWS}
    for i in ids:
        _, _, country, start, end, typology = rows[i["id"]]
        expected = format_id(country, start, end, typology, i["gbdi_number"], 1)
        assert i["gbdi_id"] == expected
