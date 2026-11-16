"""upload gbdi_id: the project id the dashboard generates (org#108)

Every stored building gets `<country>_<year>_<typology>_<number>_v1`, numbered per
country from the oldest upload (then the lower upload id). gbdi_counter keeps the
last number of each country for the uploads to come. The format is copied here, not
imported from the app, so this migration does not change when the app does.

Revision ID: e3a91c5f2b07
Revises: 7b3e9f1a2c48
Create Date: 2026-11-16

"""

from collections.abc import Sequence
from datetime import date, datetime

import sqlalchemy as sa
import sqlmodel

from alembic import op

revision: str = "e3a91c5f2b07"
down_revision: str | Sequence[str] | None = "7b3e9f1a2c48"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MISSING = "xxx"
COLUMNS = ("gbdi_id", "gbdi_country", "gbdi_number", "gbdi_version")

# (upload id, uploaded_at, project_country, start date, end date, building_use_type)
Row = tuple[int, datetime, str | None, date | None, date | None, str | None]


def assign(rows: list[Row]) -> tuple[list[dict], dict[str, int]]:
    """The id of each upload, oldest first, and the last number of each country.
    The columns hold the enums' 3-letter values, or null."""
    counters: dict[str, int] = {}
    ids = []
    for upload_id, _, country, start, end, typology in sorted(
        rows, key=lambda r: (r[1], r[0])
    ):
        country = country or MISSING
        counters[country] = number = counters.get(country, 0) + 1
        when = start or end
        year = MISSING if when is None else str(when.year)
        ids.append(
            {
                "id": upload_id,
                "gbdi_id": f"{country}_{year}_{typology or MISSING}_{number:04d}_v1",
                "gbdi_country": country,
                "gbdi_number": number,
                "gbdi_version": 1,
            }
        )
    return ids, counters


def upgrade() -> None:
    op.add_column(
        "upload",
        sa.Column("gbdi_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    )
    op.add_column(
        "upload",
        sa.Column(
            "gbdi_country", sqlmodel.sql.sqltypes.AutoString(length=3), nullable=True
        ),
    )
    op.add_column("upload", sa.Column("gbdi_number", sa.Integer(), nullable=True))
    op.add_column("upload", sa.Column("gbdi_version", sa.Integer(), nullable=True))
    op.create_table(
        "gbdi_counter",
        sa.Column(
            "country", sqlmodel.sql.sqltypes.AutoString(length=3), nullable=False
        ),
        sa.Column("last_number", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("country"),
    )

    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT u.id, u.uploaded_at, p.project_country::text,"
            " p.building_construction_start_date, p.building_construction_end_date,"
            " p.building_use_type::text"
            " FROM upload u JOIN project_record p ON p.id = u.project_record_id"
        )
    ).all()
    ids, counters = assign([tuple(r) for r in rows])
    if ids:
        bind.execute(
            sa.text(
                "UPDATE upload SET gbdi_id = :gbdi_id, gbdi_country = :gbdi_country,"
                " gbdi_number = :gbdi_number, gbdi_version = :gbdi_version"
                " WHERE id = :id"
            ),
            ids,
        )
        bind.execute(
            sa.text(
                "INSERT INTO gbdi_counter (country, last_number)"
                " VALUES (:country, :last_number)"
            ),
            [{"country": c, "last_number": n} for c, n in counters.items()],
        )

    for column in COLUMNS:
        op.alter_column("upload", column, nullable=False)
    op.create_unique_constraint(
        "uq_upload_gbdi_number",
        "upload",
        ["gbdi_country", "gbdi_number", "gbdi_version"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_upload_gbdi_number", "upload", type_="unique")
    for column in reversed(COLUMNS):
        op.drop_column("upload", column)
    op.drop_table("gbdi_counter")
