"""add cost_center to expense_claims

Revision ID: aaa0a4236100
Revises: e44d115a61f1
Create Date: 2026-11-18 17:16:28.696266

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "aaa0a4236100"
down_revision: str | Sequence[str] | None = "e44d115a61f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the optional cost_center column (spec 002).

    Nullable, so existing claims are kept as they are with cost_center = NULL: no
    server_default or backfill. The cost-center rule applies to new submissions only.
    """
    with op.batch_alter_table("expense_claims", schema=None) as batch_op:
        batch_op.add_column(sa.Column("cost_center", sa.String(length=7), nullable=True))


def downgrade() -> None:
    """Remove cost_center, restoring the baseline schema (recorded cost centers are lost)."""
    with op.batch_alter_table("expense_claims", schema=None) as batch_op:
        batch_op.drop_column("cost_center")
