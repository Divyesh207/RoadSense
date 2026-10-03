import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prediction_horizon_days: int = Field(90, ge=7, le=730, description="Forecast horizon in days (e.g. 30, 90, 180, 365)")
    target_type: str = Field("DETERIORATION_RISK", description="DETERIORATION_RISK or HEALTH_SCORE_DROP")
    persist: bool = Field(True, description="Whether to store prediction in database")


class PredictionResponseData(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    road_id: uuid.UUID | None = None
    road_segment_id: uuid.UUID
    model_id: uuid.UUID
    model_name: str
    model_version: str
    prediction_horizon_days: int
    target_type: str
    predicted_risk: float | None = None
    predicted_value: float | None = None
    uncertainty_lower: float | None = None
    uncertainty_upper: float | None = None
    confidence: float | None = None
    feature_version: str | None = None
    features: dict[str, Any] = Field(default_factory=dict)
    input_data_timestamp: datetime | None = None
    generated_at: datetime
    status: str
    # RULE_BASED_ESTIMATE (current hand-weighted rules) or TRAINED_MODEL once a real model exists.
    estimation_method: str | None = None
    disclaimer: str = (
        "Predictions are statistical decision-support estimates for proactive maintenance and "
        "must not be treated as guaranteed future outcomes."
    )
