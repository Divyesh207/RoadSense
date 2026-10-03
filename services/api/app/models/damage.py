import uuid
from datetime import datetime, timezone

from geoalchemy2 import Geometry
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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class DamageRecord(Base):
    __tablename__ = "damage_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    inspection_id = Column(UUID(as_uuid=True), ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False, index=True)
    source_detection_id = Column(UUID(as_uuid=True), ForeignKey("ai_detections.id", ondelete="SET NULL"), nullable=True, index=True)
    road_id = Column(UUID(as_uuid=True), ForeignKey("roads.id", ondelete="SET NULL"), nullable=True, index=True)
    road_segment_id = Column(UUID(as_uuid=True), ForeignKey("road_segments.id", ondelete="SET NULL"), nullable=True, index=True)
    damage_type_id = Column(UUID(as_uuid=True), ForeignKey("damage_types.id", ondelete="RESTRICT"), nullable=False, index=True)
    source_type = Column(String(30), nullable=False, default="AI")
    severity = Column(String(20), nullable=False, index=True)
    severity_score = Column(Numeric(7, 4), nullable=True)
    severity_method_version = Column(String(100), nullable=True)
    location = Column(Geometry("POINT", srid=4326, spatial_index=False), nullable=True)
    status = Column(String(30), nullable=False, default="DETECTED", index=True)
    confidence = Column(Numeric(7, 6), nullable=True)
    estimated_area_m2 = Column(Numeric(14, 4), nullable=True)
    detected_at = Column(DateTime(timezone=True), nullable=True, index=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(Text, nullable=True)
    # GPS grouping: how many inspection observations map to this physical damage.
    observation_count = Column(Integer, nullable=False, default=1, server_default="1")
    last_observed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    organization = relationship("Organization")
    inspection = relationship("Inspection", back_populates="damage_records")
    source_detection = relationship("AIDetection", back_populates="damage_records")
    road = relationship("Road", back_populates="damage_records")
    road_segment = relationship("RoadSegment", back_populates="damage_records")
    damage_type = relationship("DamageType", back_populates="damage_records")
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_user_id])
    reviews = relationship("DamageReview", back_populates="damage_record", cascade="all, delete-orphan")
    maintenance_links = relationship("MaintenanceDamageLink", back_populates="damage_record")
    observations = relationship("DamageObservation", back_populates="damage_record", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="chk_damage_confidence_range"),
        CheckConstraint("severity_score IS NULL OR (severity_score >= 0 AND severity_score <= 100)", name="chk_damage_severity_score_range"),
        CheckConstraint("estimated_area_m2 IS NULL OR estimated_area_m2 >= 0", name="chk_damage_area_nonnegative"),
        CheckConstraint("observation_count >= 1", name="chk_damage_observation_count_positive"),
        Index("damage_records_org_idx", "organization_id"),
        Index("damage_records_segment_idx", "road_segment_id"),
        Index("damage_records_severity_idx", "severity"),
        Index("damage_records_status_idx", "status"),
        Index("damage_records_detected_at_idx", "detected_at"),
        Index("damage_records_location_gist", "location", postgresql_using="gist"),
    )


class DamageObservation(Base):
    """One sighting of a physical damage: inspection -> media -> detection -> damage record.

    A detection maps to at most one damage record (unique detection_id), so the same
    detection cannot be promoted twice; repeated sightings of the same damage in later
    inspections are grouped onto one record by GPS proximity (see damage_grouping).
    """

    __tablename__ = "damage_observations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    damage_record_id = Column(UUID(as_uuid=True), ForeignKey("damage_records.id", ondelete="CASCADE"), nullable=False, index=True)
    detection_id = Column(UUID(as_uuid=True), ForeignKey("ai_detections.id", ondelete="SET NULL"), nullable=True)
    inspection_id = Column(UUID(as_uuid=True), ForeignKey("inspections.id", ondelete="CASCADE"), nullable=False, index=True)
    media_id = Column(UUID(as_uuid=True), ForeignKey("inspection_media.id", ondelete="SET NULL"), nullable=True, index=True)
    # NEW_RECORD (first sighting), GPS_GROUPED (matched an open record), MANUAL (manually entered)
    match_method = Column(String(30), nullable=False)
    distance_meters = Column(Numeric(10, 3), nullable=True)
    location = Column(Geometry("POINT", srid=4326, spatial_index=False), nullable=True)
    observed_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    damage_record = relationship("DamageRecord", back_populates="observations")

    __table_args__ = (
        UniqueConstraint("detection_id", name="uq_damage_observations_detection"),
        CheckConstraint("match_method IN ('NEW_RECORD', 'GPS_GROUPED', 'MANUAL')", name="chk_damage_observation_method"),
        CheckConstraint("distance_meters IS NULL OR distance_meters >= 0", name="chk_damage_observation_distance"),
        Index("damage_observations_location_gist", "location", postgresql_using="gist"),
    )


class DamageReview(Base):
    __tablename__ = "damage_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    damage_record_id = Column(UUID(as_uuid=True), ForeignKey("damage_records.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    review_status = Column(String(30), nullable=False)
    original_damage_type_id = Column(UUID(as_uuid=True), ForeignKey("damage_types.id", ondelete="SET NULL"), nullable=True)
    reviewed_damage_type_id = Column(UUID(as_uuid=True), ForeignKey("damage_types.id", ondelete="SET NULL"), nullable=True)
    original_severity = Column(String(20), nullable=True)
    reviewed_severity = Column(String(20), nullable=True)
    original_confidence = Column(Numeric(7, 6), nullable=True)
    review_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)

    damage_record = relationship("DamageRecord", back_populates="reviews")
    reviewer = relationship("User", foreign_keys=[reviewer_user_id])
    original_damage_type = relationship("DamageType", foreign_keys=[original_damage_type_id])
    reviewed_damage_type = relationship("DamageType", foreign_keys=[reviewed_damage_type_id])
