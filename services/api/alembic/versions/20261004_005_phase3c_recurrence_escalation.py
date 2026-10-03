"""phase 3c: recurrence rule factors and escalation

Non-destructive: nullable columns and a check constraint on recurrence_records.
Existing rows keep their values; their escalation is left NULL (never evaluated).

Revision ID: 005_phase3c_recurrence
Revises: 004_phase3b_repair_verif
Create Date: 2026-10-04 15:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005_phase3c_recurrence"
down_revision: str | None = "004_phase3b_repair_verif"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("recurrence_records", sa.Column("rule_factors", postgresql.JSONB(), nullable=True))
    op.add_column("recurrence_records", sa.Column("escalation_level", sa.String(20), nullable=True))
    op.add_column("recurrence_records", sa.Column("escalation_reasons", postgresql.JSONB(), nullable=True))
    op.add_column("recurrence_records", sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True))
    op.create_check_constraint(
        "chk_recurrence_escalation_level", "recurrence_records",
        "escalation_level IS NULL OR escalation_level IN ('NONE', 'ELEVATED', 'CRITICAL')",
    )


def downgrade() -> None:
    op.drop_constraint("chk_recurrence_escalation_level", "recurrence_records", type_="check")
    for col in ("escalated_at", "escalation_reasons", "escalation_level", "rule_factors"):
        op.drop_column("recurrence_records", col)
