"""project record: project_reference and project_doi (openbdf v0.1.5)

Revision ID: f4b8d2a6c913
Revises: e3a91c5f2b07
Create Date: 2026-11-20 10:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f4b8d2a6c913"
down_revision: str | Sequence[str] | None = "e3a91c5f2b07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "project_record",
        sa.Column("project_reference", sa.String(length=1000), nullable=True),
    )
    op.add_column(
        "project_record",
        sa.Column("project_doi", sa.String(length=200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("project_record", "project_doi")
    op.drop_column("project_record", "project_reference")
