import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MapDamageFeature(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    damage_type: str
    severity: str
    status: str
    confidence: float | None = None
    # TRAINED_MODEL / HEURISTIC_FALLBACK / MANUAL / UNKNOWN; HEURISTIC_SCORE is not a probability.
    detection_method: str | None = None
    score_type: str | None = None
    latitude: float
    longitude: float
    road_id: uuid.UUID | None = None
    road_name: str | None = None
    road_segment_id: uuid.UUID | None = None
    segment_number: int | None = None
    segment_name: str | None = None
    detected_at: datetime | None = None


class MapRoadFeature(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    road_code: str | None = None
    road_type: str | None = None
    geometry: dict[str, Any]
    length_km: float | None = None
    is_active: bool = True
    segment_count: int = 0
    damage_count: int = 0
    critical_damage_count: int = 0
    health_score: float | None = None
    health_status: str | None = None


class MapSegmentFeature(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    road_id: uuid.UUID
    road_name: str | None = None
    segment_number: int
    name: str | None = None
    start_chainage: float | None = None
    end_chainage: float | None = None
    length_meters: float | None = None
    geometry: dict[str, Any]
    damage_count: int = 0
    critical_damage_count: int = 0
    health_score: float | None = None
    health_status: str | None = None
    priority_score: float | None = None


class MapFilterParams(BaseModel):
    min_lat: float | None = Field(None, ge=-90.0, le=90.0)
    min_lon: float | None = Field(None, ge=-180.0, le=180.0)
    max_lat: float | None = Field(None, ge=-90.0, le=90.0)
    max_lon: float | None = Field(None, ge=-180.0, le=180.0)
