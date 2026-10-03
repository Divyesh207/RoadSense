"""phase 3b: image-based repair verification and human review provenance

Non-destructive: only nullable columns, constraints and indexes are added to
repair_verifications. Existing rows are labelled with the verification type they
already represent (automated evidence check or human sign-off); no row is removed
or rewritten otherwise.

Revision ID: 004_phase3b_repair_verif
Revises: 003_phase3a_foundation
Create Date: 2026-10-04 09:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004_phase3b_repair_verif"
down_revision: str | None = "003_phase3a_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    add = lambda col: op.add_column("repair_verifications", col)
    add(sa.Column("verification_type", sa.String(40), nullable=True))
    add(sa.Column("result", sa.String(20), nullable=True))
    add(sa.Column("before_evidence_id", UUID, sa.ForeignKey("repair_evidence.id", ondelete="SET NULL"), nullable=True))
    add(sa.Column("before_media_id", UUID, sa.ForeignKey("inspection_media.id", ondelete="SET NULL"), nullable=True))
    add(sa.Column("after_evidence_id", UUID, sa.ForeignKey("repair_evidence.id", ondelete="SET NULL"), nullable=True))
    add(sa.Column("processing_job_id", UUID, sa.ForeignKey("processing_jobs.id", ondelete="SET NULL"), nullable=True))
    add(sa.Column("model_name", sa.String(150), nullable=True))
    add(sa.Column("model_version", sa.String(50), nullable=True))
    add(sa.Column("algorithm_version", sa.String(50), nullable=True))
    add(sa.Column(
        "reviewed_verification_id", UUID, sa.ForeignKey("repair_verifications.id", ondelete="SET NULL"), nullable=True
    ))
    add(sa.Column("previous_result", sa.String(20), nullable=True))
    add(sa.Column("review_decision", sa.String(20), nullable=True))
    add(sa.Column("error_code", sa.String(100), nullable=True))
    add(sa.Column("error_message", sa.Text(), nullable=True))

    op.create_check_constraint(
        "chk_verification_result", "repair_verifications",
        "result IS NULL OR result IN ('SUCCESSFUL', 'SUBSTANDARD', 'UNRESOLVED')",
    )
    op.create_check_constraint(
        "chk_verification_review_decision", "repair_verifications",
        "review_decision IS NULL OR review_decision IN ('CONFIRMED', 'REJECTED', 'UNRESOLVED')",
    )
    op.create_unique_constraint("uq_repair_verifications_processing_job", "repair_verifications", ["processing_job_id"])
    op.create_index(
        "ix_repair_verifications_reviewed_verification_id", "repair_verifications", ["reviewed_verification_id"]
    )

    # Label existing rows by what they already are; their results are not reinterpreted.
    op.execute(
        "UPDATE repair_verifications SET verification_type = 'AUTOMATED_EVIDENCE_CHECK' "
        "WHERE verification_status = 'AUTOMATED_CHECK'"
    )
    op.execute(
        "UPDATE repair_verifications SET verification_type = 'HUMAN_SIGNOFF' "
        "WHERE verification_status IN ('VERIFIED', 'REJECTED') AND verified_by_user_id IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_index("ix_repair_verifications_reviewed_verification_id", table_name="repair_verifications")
    op.drop_constraint("uq_repair_verifications_processing_job", "repair_verifications", type_="unique")
    op.drop_constraint("chk_verification_review_decision", "repair_verifications", type_="check")
    op.drop_constraint("chk_verification_result", "repair_verifications", type_="check")
    for col in (
        "error_message", "error_code", "review_decision", "previous_result", "reviewed_verification_id",
        "algorithm_version", "model_version", "model_name", "processing_job_id", "after_evidence_id",
        "before_media_id", "before_evidence_id", "result", "verification_type",
    ):
        op.drop_column("repair_verifications", col)
