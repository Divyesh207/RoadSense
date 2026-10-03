import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_IMAGE_EVIDENCE_BYTES = 20 * 1024 * 1024
EVIDENCE_MIME_PATTERN = "^(image/(jpeg|png|webp)|video/(mp4|quicktime))$"


class RepairEvidenceUploadUrlRequest(BaseModel):
    filename: Annotated[str, Field(min_length=1, max_length=255)]
    content_type: Annotated[str, Field(pattern="^(image/(jpeg|png|webp)|video/(mp4|quicktime))$")]
    size_bytes: Annotated[int, Field(ge=1, le=104857600)]  # max 100MB
    evidence_type: Annotated[str, Field(default="AFTER_REPAIR", pattern="^(BEFORE_REPAIR|DURING_REPAIR|AFTER_REPAIR)$")] = "AFTER_REPAIR"

    @model_validator(mode="after")
    def _image_size_limit(self):
        if self.content_type.startswith("image/") and self.size_bytes > MAX_IMAGE_EVIDENCE_BYTES:
            raise ValueError(f"Image evidence must be at most {MAX_IMAGE_EVIDENCE_BYTES // (1024 * 1024)} MB.")
        return self


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
    mime_type: Annotated[str, Field(default="image/jpeg", pattern=EVIDENCE_MIME_PATTERN)] = "image/jpeg"
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
    verification_type: str | None = None
    result: str | None = None
    before_evidence_id: uuid.UUID | None = None
    before_media_id: uuid.UUID | None = None
    after_evidence_id: uuid.UUID | None = None
    processing_job_id: uuid.UUID | None = None
    model_name: str | None = None
    model_version: str | None = None
    algorithm_version: str | None = None
    reviewed_verification_id: uuid.UUID | None = None
    previous_result: str | None = None
    review_decision: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class RepairImageVerificationRequest(BaseModel):
    """Both default to the latest image of that kind; BEFORE falls back to the
    inspection photo of the linked damage when no BEFORE_REPAIR evidence exists."""

    before_evidence_id: uuid.UUID | None = None
    after_evidence_id: uuid.UUID | None = None


class RepairVerificationReviewRequest(BaseModel):
    decision: Literal["CONFIRMED", "REJECTED", "UNRESOLVED"]
    # Required when rejecting the automated result: the reviewer's own outcome.
    final_result: Literal["SUCCESSFUL", "SUBSTANDARD", "UNRESOLVED"] | None = None
    notes: Annotated[str | None, Field(default=None, max_length=2000)] = None

    @model_validator(mode="after")
    def _rejection_needs_outcome(self):
        if self.decision == "REJECTED" and (self.final_result is None or not (self.notes or "").strip()):
            raise ValueError("Rejecting the automated result requires final_result and reviewer notes.")
        return self


class SignedImageUrls(BaseModel):
    before_url: str | None = None
    before_source: str | None = None
    after_url: str | None = None
    expires_in_seconds: int


class EvidenceDownloadUrl(BaseModel):
    download_url: str
    expires_in_seconds: int
