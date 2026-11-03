"""upload draft: stored despite reject findings

Revision ID: 5d2a9c1e7f30
Revises: cbb06ae64c40
Create Date: 2026-11-02 15:30:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "5d2a9c1e7f30"
down_revision: str | Sequence[str] | None = "cbb06ae64c40"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Every upload stored so far passed without rejects: not a draft.
    op.add_column(
        "upload",
        sa.Column("draft", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("upload", "draft")
