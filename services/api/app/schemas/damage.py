import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.inspection import LocationInput, LocationOutput


class DamageTypeResponseData(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None = None
    is_active: bool
    created_at: datetime


class BoundingBox(BaseModel):
    x_min: float = Field(ge=0.0, le=1.0)
    y_min: float = Field(ge=0.0, le=1.0)
    x_max: float = Field(ge=0.0, le=1.0)
    y_max: float = Field(ge=0.0, le=1.0)


class AIDetectionResponseData(BaseModel):
    id: uuid.UUID
    inspection_id: uuid.UUID
    media_id: uuid.UUID
    damage_type: str
    damage_type_id: uuid.UUID
    confidence: float
    bbox: BoundingBox
    pixel_width: int | None = None
    pixel_height: int | None = None
    frame_number: int | None = None
    frame_timestamp_ms: int | None = None
    location: LocationOutput | None = None
    severity: str | None = None
    severity_factors: dict[str, Any] | None = None
    model_version: str | None = None
    created_at: datetime


class DamageReviewResponseData(BaseModel):
    id: uuid.UUID
    damage_record_id: uuid.UUID
    reviewer_user_id: uuid.UUID
    reviewer_name: str | None = None
    review_status: str
    original_damage_type_id: uuid.UUID | None = None
    reviewed_damage_type_id: uuid.UUID | None = None
    original_severity: str | None = None
    reviewed_severity: str | None = None
    original_confidence: float | None = None
    review_notes: str | None = None
    reviewed_at: datetime


class DamageRecordResponseData(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    inspection_id: uuid.UUID
    source_detection_id: uuid.UUID | None = None
    road_id: uuid.UUID | None = None
    road_name: str | None = None
    road_segment_id: uuid.UUID | None = None
    segment_number: int | None = None
    damage_type_id: uuid.UUID
    damage_type_code: str
    damage_type_name: str
    source_type: Literal["AI", "MANUAL"]
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    severity_score: float | None = None
    severity_method_version: str | None = None
    location: LocationOutput | None = None
    status: Literal[
        "DETECTED", "PENDING_REVIEW", "CONFIRMED", "REJECTED", "MAINTENANCE_SCHEDULED", "IN_PROGRESS", "REPAIRED"
    ]
    confidence: float | None = None
    # How the record was produced: TRAINED_MODEL, HEURISTIC_FALLBACK (OpenCV rules), MANUAL or UNKNOWN.
    detection_method: str | None = None
    # MODEL_CONFIDENCE (model probability) or HEURISTIC_SCORE (rule-derived score, not a probability).
    score_type: str | None = None
    estimated_area_m2: float | None = None
    # GPS grouping: number of inspection sightings of this damage and the latest one
    observation_count: int = 1
    last_observed_at: datetime | None = None
    detected_at: datetime | None = None
    reviewed_at: datetime | None = None
    reviewed_by_user_id: uuid.UUID | None = None
    reviewed_by_name: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class DamageCreateRequest(BaseModel):
    inspection_id: uuid.UUID
    damage_type_id: uuid.UUID
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"
    location: LocationInput | None = None
    road_id: uuid.UUID | None = None
    road_segment_id: uuid.UUID | None = None
    estimated_area_m2: float | None = Field(default=None, ge=0.0)
    notes: str | None = Field(default=None, max_length=2000)


class DamageUpdateRequest(BaseModel):
    damage_type_id: uuid.UUID | None = None
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] | None = None
    status: Literal["DETECTED", "PENDING_REVIEW", "CONFIRMED", "REJECTED", "REPAIRED"] | None = None
    estimated_area_m2: float | None = Field(default=None, ge=0.0)
    notes: str | None = Field(default=None, max_length=2000)


class DamageReviewRequest(BaseModel):
    decision: Literal["CONFIRMED", "REJECTED"]
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] | None = None
    damage_type_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=2000)


class DamageObservationResponseData(BaseModel):
    id: uuid.UUID
    damage_record_id: uuid.UUID
    detection_id: uuid.UUID | None = None
    inspection_id: uuid.UUID
    media_id: uuid.UUID | None = None
    match_method: str
    distance_meters: float | None = None
    location: LocationOutput | None = None
    observed_at: datetime
