import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class RecurrenceRecord(Base):
    __tablename__ = "recurrence_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    historical_damage_id = Column(UUID(as_uuid=True), ForeignKey("damage_records.id", ondelete="RESTRICT"), nullable=False, index=True)
    new_damage_id = Column(UUID(as_uuid=True), ForeignKey("damage_records.id", ondelete="RESTRICT"), nullable=False, index=True)
    related_maintenance_job_id = Column(UUID(as_uuid=True), ForeignKey("maintenance_jobs.id", ondelete="SET NULL"), nullable=True)
    related_repair_verification_id = Column(UUID(as_uuid=True), ForeignKey("repair_verifications.id", ondelete="SET NULL"), nullable=True)
    road_segment_id = Column(UUID(as_uuid=True), ForeignKey("road_segments.id", ondelete="SET NULL"), nullable=True, index=True)
    spatial_distance_meters = Column(Numeric(12, 3), nullable=True)
    temporal_distance_days = Column(Integer, nullable=True)
    similarity_score = Column(Numeric(7, 6), nullable=True)
    recurrence_score = Column(Numeric(7, 6), nullable=True)
    detection_method_version = Column(String(100), nullable=True)
    status = Column(String(30), nullable=False, default="POTENTIAL")
    evaluated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    reviewed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    review_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    organization = relationship("Organization")
    historical_damage = relationship("DamageRecord", foreign_keys=[historical_damage_id])
    new_damage = relationship("DamageRecord", foreign_keys=[new_damage_id])
    related_maintenance_job = relationship("MaintenanceJob")
    related_repair_verification = relationship("RepairVerification")
    road_segment = relationship("RoadSegment")
    reviewed_by = relationship("User")

    __table_args__ = (
        CheckConstraint("spatial_distance_meters IS NULL OR spatial_distance_meters >= 0", name="chk_recurrence_distance_nonnegative"),
        CheckConstraint("similarity_score IS NULL OR (similarity_score >= 0 AND similarity_score <= 1)", name="chk_recurrence_similarity_range"),
        CheckConstraint("recurrence_score IS NULL OR (recurrence_score >= 0 AND recurrence_score <= 1)", name="chk_recurrence_score_range"),
        Index("recurrence_records_org_idx", "organization_id"),
        Index("recurrence_records_segment_idx", "road_segment_id"),
    )


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    notification_type = Column(String(60), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    data = Column(JSONB, nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    organization = relationship("Organization")
    user = relationship("User")

    __table_args__ = (
        Index("notifications_user_idx", "user_id"),
        Index("notifications_unread_idx", "user_id", "read_at"),
        Index("notifications_created_at_idx", "created_at"),
    )


class GeneratedReport(Base):
    __tablename__ = "generated_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    requested_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    report_type = Column(String(60), nullable=False)
    status = Column(String(30), nullable=False, default="QUEUED")
    parameters = Column(JSONB, nullable=False, default=dict)
    storage_bucket = Column(String(100), nullable=True)
    storage_path = Column(Text, nullable=True)
    processing_job_id = Column(UUID(as_uuid=True), ForeignKey("processing_jobs.id", ondelete="SET NULL"), nullable=True)
    generated_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    organization = relationship("Organization")
    requested_by = relationship("User")
    job = relationship("ProcessingJob")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(80), nullable=False, index=True)
    entity_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    request_id = Column(String(100), nullable=True)
    before_data = Column(JSONB, nullable=True)
    after_data = Column(JSONB, nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)

    organization = relationship("Organization")
    actor = relationship("User")

    __table_args__ = (
        Index("audit_logs_created_idx", "created_at"),
        Index("audit_logs_action_entity_idx", "action", "entity_type"),
    )
