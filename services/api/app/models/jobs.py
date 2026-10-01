import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    job_type = Column(String(60), nullable=False, index=True)
    entity_type = Column(String(60), nullable=False)
    entity_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    idempotency_key = Column(String(255), nullable=False)
    status = Column(String(30), nullable=False, default="QUEUED", index=True)
    priority = Column(Integer, nullable=False, default=0)
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    worker_version = Column(String(100), nullable=True)
    queued_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    error_code = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    result_metadata = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    processing_runs = relationship("AIProcessingRun", back_populates="job")

    __table_args__ = (
        UniqueConstraint("organization_id", "job_type", "idempotency_key", name="uq_processing_jobs_idempotency"),
        CheckConstraint("attempts >= 0", name="chk_jobs_attempts_nonnegative"),
        CheckConstraint("max_attempts >= 1", name="chk_jobs_max_attempts_positive"),
        CheckConstraint("priority >= 0", name="chk_jobs_priority_nonnegative"),
        Index("processing_jobs_org_idx", "organization_id"),
        Index("processing_jobs_status_idx", "status"),
        Index("processing_jobs_type_idx", "job_type"),
    )
