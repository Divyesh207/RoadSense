import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def utc_now():
    return datetime.now(UTC)


class RoadHealthSnapshot(Base):
    __tablename__ = "road_health_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    road_id = Column(UUID(as_uuid=True), ForeignKey("roads.id", ondelete="SET NULL"), nullable=True, index=True)
    road_segment_id = Column(UUID(as_uuid=True), ForeignKey("road_segments.id", ondelete="SET NULL"), nullable=True, index=True)
    health_score = Column(Numeric(6, 2), nullable=True)
    health_status = Column(String(30), nullable=False, index=True)
    calculation_version = Column(String(100), nullable=False)
    input_data_timestamp = Column(DateTime(timezone=True), nullable=True)
    factors = Column(JSONB, nullable=False)
    calculation_metadata = Column(JSONB, nullable=True)
    calculated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    organization = relationship("Organization")
    road = relationship("Road")
    road_segment = relationship("RoadSegment", back_populates="health_snapshots")

    __table_args__ = (
        CheckConstraint("health_score IS NULL OR (health_score >= 0 AND health_score <= 100)", name="chk_health_score_range"),
        Index("road_health_org_idx", "organization_id"),
        Index("road_health_segment_idx", "road_segment_id"),
        Index("road_health_calculated_idx", "calculated_at"),
    )


class MaintenancePrioritySnapshot(Base):
    __tablename__ = "maintenance_priority_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    road_id = Column(UUID(as_uuid=True), ForeignKey("roads.id", ondelete="SET NULL"), nullable=True, index=True)
    road_segment_id = Column(UUID(as_uuid=True), ForeignKey("road_segments.id", ondelete="SET NULL"), nullable=True, index=True)
    priority_score = Column(Numeric(6, 2), nullable=True)
    priority_level = Column(String(30), nullable=False, index=True)
    calculation_version = Column(String(100), nullable=False)
    factors = Column(JSONB, nullable=False)
    input_data_timestamp = Column(DateTime(timezone=True), nullable=True)
    calculated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    organization = relationship("Organization")
    road = relationship("Road")
    road_segment = relationship("RoadSegment")

    __table_args__ = (
        CheckConstraint("priority_score IS NULL OR (priority_score >= 0 AND priority_score <= 100)", name="chk_priority_score_range"),
        Index("priority_org_idx", "organization_id"),
        Index("priority_segment_idx", "road_segment_id"),
    )


class DeteriorationPrediction(Base):
    __tablename__ = "deterioration_predictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    road_id = Column(UUID(as_uuid=True), ForeignKey("roads.id", ondelete="SET NULL"), nullable=True, index=True)
    road_segment_id = Column(UUID(as_uuid=True), ForeignKey("road_segments.id", ondelete="SET NULL"), nullable=True, index=True)
    model_id = Column(UUID(as_uuid=True), ForeignKey("ai_models.id", ondelete="RESTRICT"), nullable=False, index=True)
    prediction_horizon_days = Column(Integer, nullable=False)
    target_type = Column(String(60), nullable=False)
    predicted_value = Column(Numeric(14, 6), nullable=True)
    predicted_risk = Column(Numeric(6, 2), nullable=True)
    uncertainty_lower = Column(Numeric(14, 6), nullable=True)
    uncertainty_upper = Column(Numeric(14, 6), nullable=True)
    confidence = Column(Numeric(7, 6), nullable=True)
    feature_version = Column(String(100), nullable=True)
    features = Column(JSONB, nullable=False)
    input_data_timestamp = Column(DateTime(timezone=True), nullable=True)
    generated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    status = Column(String(30), nullable=False, default="GENERATED")
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    organization = relationship("Organization")
    road = relationship("Road")
    road_segment = relationship("RoadSegment", back_populates="predictions")
    model = relationship("AIModel", back_populates="predictions")

    __table_args__ = (
        CheckConstraint("prediction_horizon_days > 0", name="chk_prediction_horizon_positive"),
        CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="chk_prediction_confidence_range"),
        CheckConstraint("predicted_risk IS NULL OR (predicted_risk >= 0 AND predicted_risk <= 100)", name="chk_prediction_risk_range"),
        Index("predictions_org_idx", "organization_id"),
        Index("predictions_segment_idx", "road_segment_id"),
    )
