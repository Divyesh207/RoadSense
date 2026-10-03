import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class RecurrenceReviewRequest(BaseModel):
    status: Literal["CONFIRMED", "DISMISSED", "FALSE_POSITIVE"] = Field(
        ..., description="Review outcome for the potential recurrence"
    )
    notes: str | None = Field(None, max_length=1000, description="Notes justifying review decision")


class RecurrenceEvaluateRequest(BaseModel):
    new_damage_id: uuid.UUID | None = Field(None, description="Specific new damage record to evaluate")
    road_segment_id: uuid.UUID | None = Field(None, description="Segment to evaluate for recurrences")
    max_distance_meters: float = Field(30.0, ge=1.0, le=200.0, description="Max spatial distance threshold")


class DamageSummaryItem(BaseModel):
    id: uuid.UUID
    damage_type: str
    severity: str
    status: str
    latitude: float | None = None
    longitude: float | None = None
    detected_at: datetime | None = None


class RecurrenceRecordResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    historical_damage_id: uuid.UUID
    new_damage_id: uuid.UUID
    related_maintenance_job_id: uuid.UUID | None = None
    related_repair_verification_id: uuid.UUID | None = None
    road_segment_id: uuid.UUID | None = None
    spatial_distance_meters: float | None = None
    temporal_distance_days: int | None = None
    similarity_score: float | None = None
    recurrence_score: float | None = None
    detection_method_version: str | None = None
    status: str
    evaluated_at: datetime
    reviewed_by_user_id: uuid.UUID | None = None
    reviewed_at: datetime | None = None
    review_notes: str | None = None
    created_at: datetime
    updated_at: datetime

    # Hydrated summaries if available
    historical_damage: DamageSummaryItem | None = None
    new_damage: DamageSummaryItem | None = None
    road_name: str | None = None
    segment_name: str | None = None
    rule_factors: dict[str, Any] | None = None
    escalation_level: str | None = None
    escalation_reasons: list[dict[str, Any]] | None = None
    escalated_at: datetime | None = None


class SegmentTimelineEvent(BaseModel):
    event_type: Literal["DAMAGE_DETECTED", "MAINTENANCE_CREATED", "MAINTENANCE_COMPLETED", "REPAIR_VERIFIED", "RECURRENCE_DETECTED"]
    timestamp: datetime
    entity_id: uuid.UUID
    title: str
    description: str | None = None
    severity: str | None = None
    status: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SegmentHistoricalTimelineResponse(BaseModel):
    road_segment_id: uuid.UUID
    road_name: str | None = None
    segment_number: int | None = None
    total_events: int
    events: list[SegmentTimelineEvent]
