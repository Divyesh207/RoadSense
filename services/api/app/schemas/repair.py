import uuid
from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field


class RepairEvidenceUploadUrlRequest(BaseModel):
    filename: Annotated[str, Field(min_length=1, max_length=255)]
    content_type: Annotated[str, Field(pattern="^(image/(jpeg|png|webp)|video/(mp4|quicktime))$")]
    size_bytes: Annotated[int, Field(ge=1, le=104857600)]  # max 100MB
    evidence_type: Annotated[str, Field(default="AFTER_REPAIR", pattern="^(BEFORE_REPAIR|DURING_REPAIR|AFTER_REPAIR)$")] = "AFTER_REPAIR"


class RepairEvidenceUploadUrlResponse(BaseModel):
    upload_url: str
    storage_path: str
    storage_bucket: str
    expires_in_seconds: int = 3600
    upload_method: str = "PUT"
    upload_headers: dict[str, str] = Field(default_factory=dict)


class RepairEvidenceCompleteRequest(BaseModel):
    storage_path: Annotated[str, Field(min_length=1)]
    storage_bucket: Annotated[str, Field(default="repair-evidence")] = "repair-evidence"
    evidence_type: Annotated[str, Field(default="AFTER_REPAIR", pattern="^(BEFORE_REPAIR|DURING_REPAIR|AFTER_REPAIR)$")] = "AFTER_REPAIR"
    media_type: Annotated[str, Field(default="IMAGE", pattern="^(IMAGE|VIDEO)$")] = "IMAGE"
    mime_type: Annotated[str, Field(default="image/jpeg")] = "image/jpeg"
    file_size_bytes: Annotated[int | None, Field(default=None, ge=0)] = None
    checksum: str | None = None
    captured_at: datetime | None = None
    latitude: Annotated[float | None, Field(default=None, ge=-90.0, le=90.0)] = None
    longitude: Annotated[float | None, Field(default=None, ge=-180.0, le=180.0)] = None
    notes: str | None = None


class RepairEvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    maintenance_job_id: uuid.UUID
    uploaded_by_user_id: uuid.UUID
    evidence_type: str
    storage_bucket: str
    storage_path: str
    media_type: str
    mime_type: str
    file_size_bytes: int | None = None
    captured_at: datetime | None = None
    latitude: float | None = None
    longitude: float | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class RepairVerificationAIEvalRequest(BaseModel):
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)


class RepairVerificationSubmitRequest(BaseModel):
    decision: Annotated[str, Field(pattern="^(VERIFIED|REJECTED)$")]
    notes: Annotated[str | None, Field(default=None, max_length=2000)] = None


class RepairVerificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    maintenance_job_id: uuid.UUID
    ai_processing_run_id: uuid.UUID | None = None
    verified_by_user_id: uuid.UUID | None = None
    verification_status: str
    ai_confidence: float | None = None
    comparison_metrics: dict[str, Any] | None = None
    findings: dict[str, Any]
    reviewer_notes: str | None = None
    verified_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
