"""add cost_center to expense_claims

Revision ID: 958c695eda07
Revises: e44d115a61f1
Create Date: 2026-11-17 17:11:04.774277

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "958c695eda07"
down_revision: str | Sequence[str] | None = "e44d115a61f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add a nullable cost_center: existing claims keep NULL (no backfill needed)."""
    with op.batch_alter_table("expense_claims", schema=None) as batch_op:
        batch_op.add_column(sa.Column("cost_center", sa.String(length=7), nullable=True))


def downgrade() -> None:
    """Drop cost_center, restoring the baseline schema."""
    with op.batch_alter_table("expense_claims", schema=None) as batch_op:
        batch_op.drop_column("cost_center")
