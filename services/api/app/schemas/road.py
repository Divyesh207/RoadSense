import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class GeoJSONLineString(BaseModel):
    type: Literal["LineString"] = "LineString"
    coordinates: list[list[float]] = Field(
        ...,
        min_length=2,
        description="List of [longitude, latitude] coordinate pairs (minimum 2 points)",
    )

    @field_validator("coordinates")
    @classmethod
    def validate_coordinates(cls, v: list[list[float]]) -> list[list[float]]:
        for point in v:
            if len(point) < 2:
                raise ValueError("Each coordinate must contain [longitude, latitude].")
            lon, lat = point[0], point[1]
            if not (-180.0 <= lon <= 180.0):
                raise ValueError(f"Longitude {lon} out of range [-180, 180].")
            if not (-90.0 <= lat <= 90.0):
                raise ValueError(f"Latitude {lat} out of range [-90, 90].")
        return v


class RoadCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Official road name")
    road_code: str | None = Field(None, max_length=100, description="Unique route code e.g. NH-48")
    road_type: str | None = Field(None, max_length=50, description="HIGHWAY, ARTERIAL, URBAN, RURAL, LOCAL")
    administrative_area: str | None = Field(None, max_length=150, description="District or ward")
    description: str | None = Field(None, description="Additional context or notes")
    geometry: GeoJSONLineString | None = Field(None, description="GeoJSON LineString geometry in SRID 4326")
    traffic_volume_class: Literal["LOW", "MEDIUM", "HIGH", "VERY_HIGH"] | None = Field(
        None, description="Road-level traffic class from a documented source; null = unknown (never estimated)"
    )
    traffic_aadt: int | None = Field(None, ge=0, le=1_000_000, description="Annual average daily traffic (vehicles/day)")
    traffic_data_source: str | None = Field(None, max_length=255, description="Where the traffic figure comes from")


class RoadUpdateRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    road_code: str | None = Field(None, max_length=100)
    road_type: str | None = Field(None, max_length=50)
    administrative_area: str | None = Field(None, max_length=150)
    description: str | None = Field(None)
    geometry: GeoJSONLineString | None = Field(None)
    is_active: bool | None = Field(None)
    traffic_volume_class: Literal["LOW", "MEDIUM", "HIGH", "VERY_HIGH"] | None = Field(
        None, description="Road-level traffic class from a documented source; null = unknown (never estimated)"
    )
    traffic_aadt: int | None = Field(None, ge=0, le=1_000_000, description="Annual average daily traffic (vehicles/day)")
    traffic_data_source: str | None = Field(None, max_length=255, description="Where the traffic figure comes from")


class RoadResponseData(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    road_code: str | None = None
    road_type: str | None = None
    administrative_area: str | None = None
    description: str | None = None
    geometry: dict[str, Any] | None = None
    is_active: bool
    traffic_volume_class: str | None = None
    traffic_aadt: int | None = None
    traffic_data_source: str | None = None
    segment_count: int = 0
    created_at: datetime
    updated_at: datetime


class RoadSegmentCreateRequest(BaseModel):
    segment_number: int = Field(..., gt=0, description="Sequential 1-indexed segment number")
    name: str | None = Field(None, max_length=150, description="Optional segment name")
    start_chainage: float | None = Field(None, ge=0, description="Start chainage in kilometers")
    end_chainage: float | None = Field(None, ge=0, description="End chainage in kilometers")
    length_meters: float | None = Field(None, ge=0, description="Segment length in meters")
    geometry: GeoJSONLineString | None = Field(None, description="GeoJSON LineString in SRID 4326")


class RoadSegmentUpdateRequest(BaseModel):
    segment_number: int | None = Field(None, gt=0)
    name: str | None = Field(None, max_length=150)
    start_chainage: float | None = Field(None, ge=0)
    end_chainage: float | None = Field(None, ge=0)
    length_meters: float | None = Field(None, ge=0)
    geometry: GeoJSONLineString | None = Field(None)
    is_active: bool | None = Field(None)


class RoadSegmentResponseData(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    road_id: uuid.UUID
    segment_number: int
    name: str | None = None
    start_chainage: float | None = None
    end_chainage: float | None = None
    length_meters: float | None = None
    geometry: dict[str, Any] | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LocationMatchRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0, description="WGS84 latitude")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="WGS84 longitude")
    max_distance_meters: float = Field(50.0, gt=0, le=500.0, description="Maximum search radius in meters")


class MatchedCandidate(BaseModel):
    road_id: uuid.UUID
    road_name: str
    road_code: str | None = None
    segment_id: uuid.UUID | None = None
    segment_number: int | None = None
    distance_meters: float
    confidence_score: float
    is_uncertain: bool
    # Fraction (0..1) along the segment of the nearest point; PostGIS only
    position_along_segment: float | None = None


class LocationMatchResponseData(BaseModel):
    query_latitude: float
    query_longitude: float
    matched: bool
    best_match: MatchedCandidate | None = None
    candidates: list[MatchedCandidate] = Field(default_factory=list)
    is_uncertain: bool = False
    uncertainty_reason: str | None = None
