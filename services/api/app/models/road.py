import uuid
from datetime import datetime, timezone

from geoalchemy2 import Geometry
from sqlalchemy import (
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
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Road(Base):
    __tablename__ = "roads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    road_code = Column(String(100), nullable=True, index=True)
    road_type = Column(String(50), nullable=True)
    administrative_area = Column(String(150), nullable=True)
    description = Column(Text, nullable=True)
    geometry = Column(Geometry("LINESTRING", srid=4326), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    organization = relationship("Organization", back_populates="roads")
    segments = relationship("RoadSegment", back_populates="road", cascade="all, delete-orphan")
    inspections = relationship("Inspection", back_populates="road")
    damage_records = relationship("DamageRecord", back_populates="road")

    __table_args__ = (
        Index("roads_organization_idx", "organization_id"),
        Index("roads_code_idx", "road_code"),
        Index("roads_geometry_gist", "geometry", postgresql_using="gist"),
    )


class RoadSegment(Base):
    __tablename__ = "road_segments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    road_id = Column(UUID(as_uuid=True), ForeignKey("roads.id", ondelete="CASCADE"), nullable=False, index=True)
    segment_number = Column(Integer, nullable=False)
    name = Column(String(150), nullable=True)
    start_chainage = Column(Numeric(12, 3), nullable=True)
    end_chainage = Column(Numeric(12, 3), nullable=True)
    length_meters = Column(Numeric(12, 3), nullable=True)
    geometry = Column(Geometry("LINESTRING", srid=4326), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    road = relationship("Road", back_populates="segments")
    inspections = relationship("Inspection", back_populates="road_segment")
    damage_records = relationship("DamageRecord", back_populates="road_segment")
    health_snapshots = relationship("RoadHealthSnapshot", back_populates="road_segment")
    predictions = relationship("DeteriorationPrediction", back_populates="road_segment")

    __table_args__ = (
        UniqueConstraint("road_id", "segment_number", name="uq_road_segments_road_segment_number"),
        CheckConstraint("segment_number > 0", name="chk_road_segments_segment_number_positive"),
        CheckConstraint("length_meters IS NULL OR length_meters >= 0", name="chk_road_segments_length_nonnegative"),
        Index("road_segments_organization_idx", "organization_id"),
        Index("road_segments_road_idx", "road_id"),
        Index("road_segments_geometry_gist", "geometry", postgresql_using="gist"),
    )
