import uuid
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field


class MaintenanceJobCreate(BaseModel):
    road_id: uuid.UUID | None = None
    road_segment_id: uuid.UUID | None = None
    title: Annotated[str, Field(min_length=3, max_length=255)]
    description: str | None = None
    priority: Annotated[str, Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")]
    priority_score: Annotated[float | None, Field(default=None, ge=0.0, le=100.0)] = None
    due_at: datetime | None = None
    target_date: str | None = None
    assigned_to_user_id: uuid.UUID | None = None
    assigned_to_organization_id: uuid.UUID | None = None
    damage_record_ids: list[uuid.UUID] = Field(default_factory=list)
    latitude: Annotated[float | None, Field(default=None, ge=-90.0, le=90.0)] = None
    longitude: Annotated[float | None, Field(default=None, ge=-180.0, le=180.0)] = None


class MaintenanceJobUpdate(BaseModel):
    title: Annotated[str | None, Field(default=None, min_length=3, max_length=255)] = None
    description: str | None = None
    priority_level: Annotated[str | None, Field(default=None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")] = None
    priority_score: Annotated[float | None, Field(default=None, ge=0.0, le=100.0)] = None
    due_at: datetime | None = None
    completion_notes: str | None = None


class MaintenanceJobAssign(BaseModel):
    assigned_to: uuid.UUID | None = None
    assigned_to_user_id: uuid.UUID | None = None
    assigned_to_organization_id: uuid.UUID | None = None


class MaintenanceStatusTransition(BaseModel):
    status: Annotated[
        str,
        Field(
            pattern="^(OPEN|ASSIGNED|IN_PROGRESS|COMPLETED|VERIFICATION_PENDING|VERIFIED|REJECTED|CANCELLED)$"
        ),
    ]
    notes: str | None = None
    reason: str | None = None


class MaintenanceDamageLinkCreate(BaseModel):
    damage_record_id: uuid.UUID
    relationship_type: Annotated[
        str,
        Field(default="PRIMARY", pattern="^(PRIMARY|RELATED|RECURRENCE|GROUPED)$"),
    ] = "PRIMARY"


class MaintenanceDamageLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    maintenance_job_id: uuid.UUID
    damage_record_id: uuid.UUID
    relationship_type: str
    created_at: datetime
    severity: str | None = None
    status: str | None = None
    damage_type: str | None = None


class MaintenanceStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    maintenance_job_id: uuid.UUID
    previous_status: str | None = None
    new_status: str
    changed_by_user_id: uuid.UUID
    reason: str | None = None
    changed_at: datetime


class MaintenanceJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    road_id: uuid.UUID | None = None
    road_segment_id: uuid.UUID | None = None
    created_by_user_id: uuid.UUID
    assigned_to_user_id: uuid.UUID | None = None
    assigned_to_organization_id: uuid.UUID | None = None
    title: str
    description: str | None = None
    priority_level: str
    priority_score: float | None = None
    # Rule-based priority inputs/components and mode (AUTO / MANUAL / MANUAL_LEVEL)
    priority_factors: dict[str, Any] | None = None
    status: str
    due_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    verified_at: datetime | None = None
    completion_notes: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    created_at: datetime
    updated_at: datetime
    damage_count: int = 0
    linked_damages: list[dict[str, Any]] = Field(default_factory=list)
