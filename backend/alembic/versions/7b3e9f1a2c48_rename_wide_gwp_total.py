"""rename the wide whole-life total gwp_total to gwp_total_total

openbdf renamed the field (lmc-openbdf c6fe287), so every indicator total ends in
_total. The tall table keeps its gwp_total column: there it holds one stage.

Revision ID: 7b3e9f1a2c48
Revises: 4effa5a4a09d
Create Date: 2026-11-11

"""

from collections.abc import Sequence

from alembic import op

revision: str = "7b3e9f1a2c48"
down_revision: str | Sequence[str] | None = "4effa5a4a09d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "lca_results_full_record", "gwp_total", new_column_name="gwp_total_total"
    )


def downgrade() -> None:
    op.alter_column(
        "lca_results_full_record", "gwp_total_total", new_column_name="gwp_total"
    )
