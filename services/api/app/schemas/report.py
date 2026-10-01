import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class ReportCreateRequest(BaseModel):
    report_type: str = Field(..., description="Report type (e.g. ROAD_HEALTH, DAMAGE_SUMMARY, MAINTENANCE_LOG)")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Filter parameters like road_id, date range, format")


class ReportCreateResponseData(BaseModel):
    report_id: uuid.UUID
    status: str
    report_type: str
    created_at: datetime


class ReportResponseData(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    requested_by_user_id: uuid.UUID
    report_type: str
    status: str
    parameters: dict[str, Any]
    storage_path: str | None = None
    generated_at: datetime | None = None
    expires_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime


class ReportDownloadUrlResponseData(BaseModel):
    report_id: uuid.UUID
    download_url: str
    expires_in_seconds: int
