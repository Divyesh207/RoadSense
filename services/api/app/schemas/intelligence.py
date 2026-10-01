import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RoadHealthFactors(BaseModel):
    model_config = ConfigDict(extra="allow")

    damage_density: float | None = None
    total_damages: int = 0
    severity_breakdown: dict[str, int] = Field(default_factory=dict)
    recurrence_count: int = 0
    inspection_freshness_days: int | None = None
    score_deductions: dict[str, float] = Field(default_factory=dict)


class RoadHealthResponseData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    road_id: uuid.UUID | None = None
    road_segment_id: uuid.UUID | None = None
    health_score: float | None = None
    health_status: str
    calculation_version: str
    input_data_timestamp: datetime | None = None
    factors: dict[str, Any] = Field(default_factory=dict)
    calculation_metadata: dict[str, Any] | None = None
    calculated_at: datetime
    created_at: datetime


class RoadHealthCalculationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notes: str | None = None
    persist_snapshot: bool = True
