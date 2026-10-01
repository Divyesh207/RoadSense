import uuid
from datetime import datetime, timezone

from geoalchemy2 import Geometry
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class MaintenanceJob(Base):
    __tablename__ = "maintenance_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    road_id = Column(UUID(as_uuid=True), ForeignKey("roads.id", ondelete="SET NULL"), nullable=True, index=True)
    road_segment_id = Column(UUID(as_uuid=True), ForeignKey("road_segments.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    assigned_to_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    assigned_to_organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    priority_level = Column(String(30), nullable=False, default="MEDIUM")
    priority_score = Column(Numeric(6, 2), nullable=True)
    status = Column(String(40), nullable=False, default="OPEN", index=True)
    due_at = Column(DateTime(timezone=True), nullable=True, index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    location = Column(Geometry("POINT", srid=4326, spatial_index=False), nullable=True)
    completion_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    organization = relationship("Organization", foreign_keys=[organization_id], back_populates="maintenance_jobs")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    assigned_to = relationship("User", foreign_keys=[assigned_to_user_id])
    assigned_organization = relationship("Organization", foreign_keys=[assigned_to_organization_id])
    road = relationship("Road")
    road_segment = relationship("RoadSegment")

    damage_links = relationship("MaintenanceDamageLink", back_populates="maintenance_job", cascade="all, delete-orphan")
    status_history = relationship("MaintenanceStatusHistory", back_populates="maintenance_job", cascade="all, delete-orphan")
    evidence = relationship("RepairEvidence", back_populates="maintenance_job", cascade="all, delete-orphan")
    verifications = relationship("RepairVerification", back_populates="maintenance_job", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("priority_score IS NULL OR (priority_score >= 0 AND priority_score <= 100)", name="chk_maintenance_priority_score_range"),
        Index("maintenance_jobs_org_idx", "organization_id"),
        Index("maintenance_jobs_status_idx", "status"),
        Index("maintenance_jobs_assigned_idx", "assigned_to_user_id"),
        Index("maintenance_jobs_due_idx", "due_at"),
        Index("maintenance_jobs_location_gist", "location", postgresql_using="gist"),
    )


class MaintenanceDamageLink(Base):
    __tablename__ = "maintenance_damage_links"

    maintenance_job_id = Column(UUID(as_uuid=True), ForeignKey("maintenance_jobs.id", ondelete="CASCADE"), primary_key=True)
    damage_record_id = Column(UUID(as_uuid=True), ForeignKey("damage_records.id", ondelete="CASCADE"), primary_key=True)
    relationship_type = Column(String(40), nullable=False, default="PRIMARY")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    maintenance_job = relationship("MaintenanceJob", back_populates="damage_links")
    damage_record = relationship("DamageRecord", back_populates="maintenance_links")


class MaintenanceStatusHistory(Base):
    __tablename__ = "maintenance_status_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    maintenance_job_id = Column(UUID(as_uuid=True), ForeignKey("maintenance_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_status = Column(String(40), nullable=True)
    new_status = Column(String(40), nullable=False)
    changed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    reason = Column(Text, nullable=True)
    changed_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    maintenance_job = relationship("MaintenanceJob", back_populates="status_history")
    changed_by = relationship("User")
