import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class LocationInput(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    accuracy_m: float | None = Field(None, ge=0.0)
    heading_deg: float | None = Field(None, ge=0.0, le=360.0)
    speed_mps: float | None = Field(None, ge=0.0)


class LocationOutput(BaseModel):
    latitude: float
    longitude: float
    accuracy_m: float | None = None


class InspectionCreateRequest(BaseModel):
    client_id: uuid.UUID | None = Field(None, description="Client device UUID for offline synchronization")
    road_id: uuid.UUID | None = None
    road_segment_id: uuid.UUID | None = None
    inspection_type: str = Field("FIELD", max_length=30)
    captured_at: datetime | None = None
    location: LocationInput | None = None
    notes: str | None = None


class InspectionUpdateRequest(BaseModel):
    notes: str | None = None
    road_id: uuid.UUID | None = None
    road_segment_id: uuid.UUID | None = None


class InspectionMediaSummary(BaseModel):
    media_count: int = 0
    image_count: int = 0
    video_count: int = 0


class InspectionResponseData(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    inspector_user_id: uuid.UUID
    inspector_name: str | None = None
    road_id: uuid.UUID | None = None
    road_name: str | None = None
    road_segment_id: uuid.UUID | None = None
    segment_number: int | None = None
    status: str
    source: str
    captured_at: datetime | None = None
    submitted_at: datetime | None = None
    location: LocationOutput | None = None
    notes: str | None = None
    client_inspection_id: uuid.UUID | None = None
    media_summary: InspectionMediaSummary = Field(default_factory=InspectionMediaSummary)
    created_at: datetime
    updated_at: datetime


class MediaUploadUrlRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., min_length=3, max_length=100)
    size_bytes: int = Field(..., gt=0)
    checksum: str | None = Field(None, max_length=128)


class MediaUploadUrlResponseData(BaseModel):
    upload_url: str
    storage_path: str
    storage_bucket: str
    expires_in: int
    # How to send the file bytes to upload_url (signed PUT for both backends).
    upload_method: str = "PUT"
    upload_headers: dict[str, str] = Field(default_factory=dict)


class MediaUploadCompleteRequest(BaseModel):
    storage_path: str = Field(..., min_length=1)
    storage_bucket: str = Field("inspection-media", min_length=1, max_length=100)
    media_type: Literal["IMAGE", "VIDEO"]
    mime_type: str = Field(..., min_length=3, max_length=100)
    size_bytes: int = Field(..., gt=0)
    original_filename: str | None = Field(None, max_length=255)
    checksum: str | None = Field(None, max_length=128)
    captured_at: datetime | None = None
    duration_seconds: float | None = Field(None, ge=0.0)
    width_px: int | None = Field(None, gt=0)
    height_px: int | None = Field(None, gt=0)
    location: LocationInput | None = None


class InspectionMediaResponseData(BaseModel):
    id: uuid.UUID
    inspection_id: uuid.UUID
    media_type: str
    storage_bucket: str
    storage_path: str
    original_filename: str | None = None
    mime_type: str
    file_size_bytes: int | None = None
    checksum: str | None = None
    upload_status: str
    duration_seconds: float | None = None
    width_px: int | None = None
    height_px: int | None = None
    created_at: datetime
    # Short-lived signed URL to view the object. Only set when the list is requested with include_urls.
    download_url: str | None = None


class ProcessInspectionResponseData(BaseModel):
    job_id: uuid.UUID
    status: str
    inspection_id: uuid.UUID


class ProcessingJobResponseData(BaseModel):
    id: uuid.UUID
    job_type: str
    entity_type: str
    entity_id: uuid.UUID
    status: str
    priority: int
    attempts: int
    max_attempts: int
    queued_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    failed_at: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None
