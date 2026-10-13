import uuid
from datetime import UTC, datetime

from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def utc_now():
    return datetime.now(UTC)


class RepairEvidence(Base):
    __tablename__ = "repair_evidence"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    maintenance_job_id = Column(UUID(as_uuid=True), ForeignKey("maintenance_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    uploaded_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    evidence_type = Column(String(30), nullable=False)
    storage_bucket = Column(String(100), nullable=False)
    storage_path = Column(Text, nullable=False)
    media_type = Column(String(20), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=True)
    checksum = Column(String(128), nullable=True)
    captured_at = Column(DateTime(timezone=True), nullable=True)
    location = Column(Geometry("POINT", srid=4326, spatial_index=False), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    maintenance_job = relationship("MaintenanceJob", back_populates="evidence")
    uploaded_by = relationship("User")

    __table_args__ = (
        CheckConstraint("file_size_bytes IS NULL OR file_size_bytes >= 0", name="chk_repair_evidence_size_nonnegative"),
        Index("repair_evidence_org_idx", "organization_id"),
        Index("repair_evidence_job_idx", "maintenance_job_id"),
        Index("repair_evidence_location_gist", "location", postgresql_using="gist"),
    )


class RepairVerification(Base):
    __tablename__ = "repair_verifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    maintenance_job_id = Column(UUID(as_uuid=True), ForeignKey("maintenance_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    ai_processing_run_id = Column(UUID(as_uuid=True), ForeignKey("ai_processing_runs.id", ondelete="SET NULL"), nullable=True)
    verified_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verification_status = Column(String(40), nullable=False, default="PENDING", index=True)
    ai_confidence = Column(Numeric(7, 6), nullable=True)
    comparison_metrics = Column(JSONB, nullable=True)
    findings = Column(JSONB, nullable=False, default=dict)
    reviewer_notes = Column(Text, nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    # Phase 3B: image-based verification and human review provenance.
    # verification_type: AUTOMATED_IMAGE_ANALYSIS | HUMAN_REVIEW | HUMAN_SIGNOFF | AUTOMATED_EVIDENCE_CHECK
    verification_type = Column(String(40), nullable=True)
    result = Column(String(20), nullable=True)  # SUCCESSFUL | SUBSTANDARD | UNRESOLVED
    before_evidence_id = Column(UUID(as_uuid=True), ForeignKey("repair_evidence.id", ondelete="SET NULL"), nullable=True)
    before_media_id = Column(UUID(as_uuid=True), ForeignKey("inspection_media.id", ondelete="SET NULL"), nullable=True)
    after_evidence_id = Column(UUID(as_uuid=True), ForeignKey("repair_evidence.id", ondelete="SET NULL"), nullable=True)
    processing_job_id = Column(UUID(as_uuid=True), ForeignKey("processing_jobs.id", ondelete="SET NULL"), nullable=True)
    model_name = Column(String(150), nullable=True)
    model_version = Column(String(50), nullable=True)
    algorithm_version = Column(String(50), nullable=True)
    # A HUMAN_REVIEW row points at the automated row it reviewed; that row is never modified.
    reviewed_verification_id = Column(
        UUID(as_uuid=True), ForeignKey("repair_verifications.id", ondelete="SET NULL"), nullable=True, index=True
    )
    previous_result = Column(String(20), nullable=True)
    review_decision = Column(String(20), nullable=True)  # CONFIRMED | REJECTED | UNRESOLVED
    error_code = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    maintenance_job = relationship("MaintenanceJob", back_populates="verifications")
    ai_processing_run = relationship("AIProcessingRun")
    verified_by = relationship("User")

    __table_args__ = (
        CheckConstraint("ai_confidence IS NULL OR (ai_confidence >= 0 AND ai_confidence <= 1)", name="chk_verification_confidence_range"),
        CheckConstraint(
            "result IS NULL OR result IN ('SUCCESSFUL', 'SUBSTANDARD', 'UNRESOLVED')", name="chk_verification_result"
        ),
        CheckConstraint(
            "review_decision IS NULL OR review_decision IN ('CONFIRMED', 'REJECTED', 'UNRESOLVED')",
            name="chk_verification_review_decision",
        ),
        UniqueConstraint("processing_job_id", name="uq_repair_verifications_processing_job"),
        Index("repair_verifications_org_idx", "organization_id"),
        Index("repair_verifications_job_idx", "maintenance_job_id"),
    )
