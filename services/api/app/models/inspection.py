import uuid
from datetime import datetime, timezone

from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger,
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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    inspector_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    road_id = Column(UUID(as_uuid=True), ForeignKey("roads.id", ondelete="SET NULL"), nullable=True, index=True)
    road_segment_id = Column(UUID(as_uuid=True), ForeignKey("road_segments.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(40), nullable=False, default="DRAFT", index=True)
    source = Column(String(30), nullable=False, default="ANDROID")
    captured_at = Column(DateTime(timezone=True), nullable=True, index=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    location = Column(Geometry("POINT", srid=4326, spatial_index=False), nullable=True)
    gps_accuracy_meters = Column(Numeric(10, 3), nullable=True)
    notes = Column(Text, nullable=True)
    failure_code = Column(String(100), nullable=True)
    failure_message = Column(Text, nullable=True)
    client_inspection_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    organization = relationship("Organization", back_populates="inspections")
    inspector = relationship("User", back_populates="inspections")
    road = relationship("Road", back_populates="inspections")
    road_segment = relationship("RoadSegment", back_populates="inspections")
    media = relationship("InspectionMedia", back_populates="inspection", cascade="all, delete-orphan")
    damage_records = relationship("DamageRecord", back_populates="inspection")
    detections = relationship("AIDetection", back_populates="inspection")

    __table_args__ = (
        CheckConstraint("gps_accuracy_meters IS NULL OR gps_accuracy_meters >= 0", name="chk_inspections_accuracy_nonnegative"),
        Index("inspections_organization_idx", "organization_id"),
        Index("inspections_inspector_idx", "inspector_user_id"),
        Index("inspections_road_idx", "road_id"),
        Index("inspections_segment_idx", "road_segment_id"),
        Index("inspections_status_idx", "status"),
        Index("inspections_captured_at_idx", "captured_at"),
        Index("inspections_location_gist", "location", postgresql_using="gist"),
    )


class InspectionMedia(Base):
    __tablename__ = "inspection_media"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    inspection_id = Column(UUID(as_uuid=True), ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False, index=True)
    media_type = Column(String(20), nullable=False)
    storage_bucket = Column(String(100), nullable=False)
    storage_path = Column(Text, nullable=False)
    original_filename = Column(String(255), nullable=True)
    mime_type = Column(String(100), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=True)
    checksum = Column(String(128), nullable=True)
    captured_at = Column(DateTime(timezone=True), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), nullable=True)
    location = Column(Geometry("POINT", srid=4326), nullable=True)
    duration_seconds = Column(Numeric(12, 3), nullable=True)
    width_px = Column(Integer, nullable=True)
    height_px = Column(Integer, nullable=True)
    frame_rate = Column(Numeric(8, 3), nullable=True)
    upload_status = Column(String(30), nullable=False, default="PENDING")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    inspection = relationship("Inspection", back_populates="media")
    detections = relationship("AIDetection", back_populates="media")

    __table_args__ = (
        CheckConstraint("file_size_bytes IS NULL OR file_size_bytes >= 0", name="chk_media_size_nonnegative"),
        CheckConstraint("duration_seconds IS NULL OR duration_seconds >= 0", name="chk_media_duration_nonnegative"),
        CheckConstraint("width_px IS NULL OR width_px > 0", name="chk_media_width_positive"),
        CheckConstraint("height_px IS NULL OR height_px > 0", name="chk_media_height_positive"),
        Index("inspection_media_org_idx", "organization_id"),
        Index("inspection_media_inspection_idx", "inspection_id"),
    )
