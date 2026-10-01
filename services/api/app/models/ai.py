import uuid
from datetime import datetime, timezone

from geoalchemy2 import Geometry
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class AIModel(Base):
    __tablename__ = "ai_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    name = Column(String(150), nullable=False)
    model_family = Column(String(100), nullable=False)
    model_type = Column(String(50), nullable=False)
    version = Column(String(50), nullable=False)
    artifact_uri = Column(Text, nullable=False)
    artifact_checksum = Column(String(128), nullable=True)
    dataset_version = Column(String(100), nullable=True)
    configuration_version = Column(String(100), nullable=True)
    framework = Column(String(100), nullable=True)
    status = Column(String(30), nullable=False, default="ACTIVE")
    metrics = Column(JSONB, nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=True)
    trained_at = Column(DateTime(timezone=True), nullable=True)
    deployed_at = Column(DateTime(timezone=True), nullable=True)
    retired_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    processing_runs = relationship("AIProcessingRun", back_populates="model")
    predictions = relationship("DeteriorationPrediction", back_populates="model")

    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_ai_models_name_version"),
        Index("ai_models_status_idx", "status"),
        Index("ai_models_type_idx", "model_type"),
    )


class AIProcessingRun(Base):
    __tablename__ = "ai_processing_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    processing_job_id = Column(UUID(as_uuid=True), ForeignKey("processing_jobs.id", ondelete="SET NULL"), nullable=True)
    model_id = Column(UUID(as_uuid=True), ForeignKey("ai_models.id", ondelete="RESTRICT"), nullable=False, index=True)
    inspection_id = Column(UUID(as_uuid=True), ForeignKey("inspections.id", ondelete="SET NULL"), nullable=True)
    media_id = Column(UUID(as_uuid=True), ForeignKey("inspection_media.id", ondelete="SET NULL"), nullable=True)
    run_type = Column(String(50), nullable=False)
    configuration_version = Column(String(100), nullable=True)
    confidence_threshold = Column(Numeric(6, 5), nullable=True)
    input_metadata = Column(JSONB, nullable=True)
    output_metadata = Column(JSONB, nullable=True)
    status = Column(String(30), nullable=False, default="QUEUED")
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    model = relationship("AIModel", back_populates="processing_runs")
    job = relationship("ProcessingJob", back_populates="processing_runs")
    detections = relationship("AIDetection", back_populates="processing_run")


class DamageType(Base):
    __tablename__ = "damage_types"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(50), nullable=False, unique=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    detections = relationship("AIDetection", back_populates="damage_type")
    damage_records = relationship("DamageRecord", back_populates="damage_type")


class AIDetection(Base):
    __tablename__ = "ai_detections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    ai_processing_run_id = Column(UUID(as_uuid=True), ForeignKey("ai_processing_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    inspection_id = Column(UUID(as_uuid=True), ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False, index=True)
    media_id = Column(UUID(as_uuid=True), ForeignKey("inspection_media.id", ondelete="CASCADE"), nullable=False, index=True)
    damage_type_id = Column(UUID(as_uuid=True), ForeignKey("damage_types.id", ondelete="RESTRICT"), nullable=False, index=True)
    frame_number = Column(Integer, nullable=True)
    frame_timestamp_ms = Column(BigInteger, nullable=True)
    confidence = Column(Numeric(7, 6), nullable=False)
    bbox_x_min = Column(Numeric(10, 7), nullable=False)
    bbox_y_min = Column(Numeric(10, 7), nullable=False)
    bbox_x_max = Column(Numeric(10, 7), nullable=False)
    bbox_y_max = Column(Numeric(10, 7), nullable=False)
    pixel_width = Column(Integer, nullable=True)
    pixel_height = Column(Integer, nullable=True)
    location = Column(Geometry("POINT", srid=4326, spatial_index=False), nullable=True)
    raw_output = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    processing_run = relationship("AIProcessingRun", back_populates="detections")
    inspection = relationship("Inspection", back_populates="detections")
    media = relationship("InspectionMedia", back_populates="detections")
    damage_type = relationship("DamageType", back_populates="detections")
    damage_records = relationship("DamageRecord", back_populates="source_detection")

    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="chk_detections_confidence_range"),
        CheckConstraint("bbox_x_min >= 0 AND bbox_x_min <= 1", name="chk_bbox_x_min"),
        CheckConstraint("bbox_y_min >= 0 AND bbox_y_min <= 1", name="chk_bbox_y_min"),
        CheckConstraint("bbox_x_max >= 0 AND bbox_x_max <= 1", name="chk_bbox_x_max"),
        CheckConstraint("bbox_y_max >= 0 AND bbox_y_max <= 1", name="chk_bbox_y_max"),
        CheckConstraint("bbox_x_min < bbox_x_max", name="chk_bbox_x_order"),
        CheckConstraint("bbox_y_min < bbox_y_max", name="chk_bbox_y_order"),
        Index("ai_detections_org_idx", "organization_id"),
        Index("ai_detections_inspection_idx", "inspection_id"),
        Index("ai_detections_media_idx", "media_id"),
        Index("ai_detections_run_idx", "ai_processing_run_id"),
        Index("ai_detections_damage_type_idx", "damage_type_id"),
        Index("ai_detections_location_gist", "location", postgresql_using="gist"),
    )
