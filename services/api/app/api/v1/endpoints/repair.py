import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from geoalchemy2.shape import to_shape
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import OrgContext, require_permission
from app.core.database import get_db
from app.models.repair import RepairEvidence, RepairVerification
from app.schemas.common import ResponseEnvelope
from app.schemas.repair import (
    EvidenceDownloadUrl,
    RepairEvidenceCompleteRequest,
    RepairEvidenceResponse,
    RepairEvidenceUploadUrlRequest,
    RepairEvidenceUploadUrlResponse,
    RepairImageVerificationRequest,
    RepairVerificationAIEvalRequest,
    RepairVerificationResponse,
    RepairVerificationReviewRequest,
    RepairVerificationSubmitRequest,
    SignedImageUrls,
)
from app.services.repair_service import (
    complete_repair_evidence,
    generate_evidence_upload_url,
    list_job_evidence,
    list_job_verifications,
    run_ai_repair_verification,
    submit_human_verification,
)
from app.services.repair_verification_service import (
    SIGNED_URL_TTL_SECONDS,
    evidence_download_url,
    request_image_verification,
    review_image_verification,
    verification_image_urls,
)

router = APIRouter()


def build_evidence_response(ev: RepairEvidence) -> RepairEvidenceResponse:
    lat, lon = None, None
    if ev.location is not None:
        try:
            pt = to_shape(ev.location)
            lat, lon = pt.y, pt.x
        except (AttributeError, ValueError, TypeError):
            pass

    return RepairEvidenceResponse(
        id=ev.id,
        organization_id=ev.organization_id,
        maintenance_job_id=ev.maintenance_job_id,
        uploaded_by_user_id=ev.uploaded_by_user_id,
        evidence_type=ev.evidence_type,
        storage_bucket=ev.storage_bucket,
        storage_path=ev.storage_path,
        media_type=ev.media_type,
        mime_type=ev.mime_type,
        file_size_bytes=ev.file_size_bytes,
        captured_at=ev.captured_at,
        latitude=lat,
        longitude=lon,
        notes=ev.notes,
        created_at=ev.created_at,
        updated_at=ev.updated_at,
    )


def build_verification_response(ver: RepairVerification) -> RepairVerificationResponse:
    return RepairVerificationResponse(
        id=ver.id,
        organization_id=ver.organization_id,
        maintenance_job_id=ver.maintenance_job_id,
        ai_processing_run_id=ver.ai_processing_run_id,
        verified_by_user_id=ver.verified_by_user_id,
        verification_status=ver.verification_status,
        ai_confidence=float(ver.ai_confidence) if ver.ai_confidence is not None else None,
        comparison_metrics=ver.comparison_metrics,
        findings=ver.findings or {},
        reviewer_notes=ver.reviewer_notes,
        verified_at=ver.verified_at,
        verification_type=ver.verification_type,
        result=ver.result,
        before_evidence_id=ver.before_evidence_id,
        before_media_id=ver.before_media_id,
        after_evidence_id=ver.after_evidence_id,
        processing_job_id=ver.processing_job_id,
        model_name=ver.model_name,
        model_version=ver.model_version,
        algorithm_version=ver.algorithm_version,
        reviewed_verification_id=ver.reviewed_verification_id,
        previous_result=ver.previous_result,
        review_decision=ver.review_decision,
        error_code=ver.error_code,
        error_message=ver.error_message,
        created_at=ver.created_at,
        updated_at=ver.updated_at,
    )


@router.post(
    "/{maintenance_job_id}/repair-evidence/upload-url",
    response_model=ResponseEnvelope[RepairEvidenceUploadUrlResponse],
    summary="Generate presigned upload URL for repair evidence media",
)
async def get_repair_evidence_upload_url(
    maintenance_job_id: uuid.UUID,
    payload: RepairEvidenceUploadUrlRequest,
    request: Request,
    org_context: Annotated[OrgContext, Depends(require_permission("maintenance:update"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    res = await generate_evidence_upload_url(
        db=db,
        maintenance_job_id=maintenance_job_id,
        organization_id=org_context.organization_id,
        payload=payload,
    )
    return ResponseEnvelope(data=res)


@router.post(
    "/{maintenance_job_id}/repair-evidence/complete",
    response_model=ResponseEnvelope[RepairEvidenceResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Complete repair evidence upload and link to maintenance job",
)
async def complete_evidence(
    maintenance_job_id: uuid.UUID,
    payload: RepairEvidenceCompleteRequest,
    request: Request,
    org_context: Annotated[OrgContext, Depends(require_permission("maintenance:update"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ev = await complete_repair_evidence(
        db=db,
        maintenance_job_id=maintenance_job_id,
        organization_id=org_context.organization_id,
        user_id=org_context.user_id,
        payload=payload,
    )
    return ResponseEnvelope(data=build_evidence_response(ev))


@router.get(
    "/{maintenance_job_id}/repair-evidence",
    response_model=ResponseEnvelope[list[RepairEvidenceResponse]],
    summary="List all repair evidence items associated with a maintenance job",
)
async def get_evidence_list(
    maintenance_job_id: uuid.UUID,
    request: Request,
    org_context: Annotated[OrgContext, Depends(require_permission("maintenance:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    items = await list_job_evidence(
        db=db,
        maintenance_job_id=maintenance_job_id,
        organization_id=org_context.organization_id,
    )
    return ResponseEnvelope(data=[build_evidence_response(i) for i in items])


@router.post(
    "/{maintenance_job_id}/ai-verify",
    response_model=ResponseEnvelope[RepairVerificationResponse],
    summary="Run automated evidence checks (presence + GPS location; no image analysis) on repair evidence",
)
async def trigger_ai_repair_verification(
    maintenance_job_id: uuid.UUID,
    request: Request,
    org_context: Annotated[OrgContext, Depends(require_permission("maintenance:update"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    payload: RepairVerificationAIEvalRequest | None = None,
):
    ev_ids = payload.evidence_ids if payload else None
    ver = await run_ai_repair_verification(
        db=db,
        maintenance_job_id=maintenance_job_id,
        organization_id=org_context.organization_id,
        evidence_ids=ev_ids,
    )
    return ResponseEnvelope(data=build_verification_response(ver))


@router.post(
    "/{maintenance_job_id}/verify",
    response_model=ResponseEnvelope[RepairVerificationResponse],
    summary="Submit human verification decision for maintenance repair",
)
async def submit_verification_decision(
    maintenance_job_id: uuid.UUID,
    payload: RepairVerificationSubmitRequest,
    request: Request,
    org_context: Annotated[OrgContext, Depends(require_permission("maintenance:verify"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    ver = await submit_human_verification(
        db=db,
        maintenance_job_id=maintenance_job_id,
        organization_id=org_context.organization_id,
        user_id=org_context.user_id,
        payload=payload,
    )
    return ResponseEnvelope(data=build_verification_response(ver))


@router.get(
    "/{maintenance_job_id}/verifications",
    response_model=ResponseEnvelope[list[RepairVerificationResponse]],
    summary="List verification history and automated check records for a job",
)
async def get_verifications_list(
    maintenance_job_id: uuid.UUID,
    request: Request,
    org_context: Annotated[OrgContext, Depends(require_permission("maintenance:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    items = await list_job_verifications(
        db=db,
        maintenance_job_id=maintenance_job_id,
        organization_id=org_context.organization_id,
    )
    return ResponseEnvelope(data=[build_verification_response(i) for i in items])


@router.get(
    "/{maintenance_job_id}/repair-evidence/{evidence_id}/download-url",
    response_model=ResponseEnvelope[EvidenceDownloadUrl],
    summary="Short-lived signed URL to view one repair evidence object",
)
async def get_evidence_download_url(
    maintenance_job_id: uuid.UUID,
    evidence_id: uuid.UUID,
    org_context: Annotated[OrgContext, Depends(require_permission("maintenance:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    url = await evidence_download_url(db, maintenance_job_id, evidence_id, org_context.organization_id)
    return ResponseEnvelope(data=EvidenceDownloadUrl(download_url=url, expires_in_seconds=SIGNED_URL_TTL_SECONDS))


@router.post(
    "/{maintenance_job_id}/repair-verifications",
    response_model=ResponseEnvelope[RepairVerificationResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Queue before/after image analysis (OpenCV alignment + trained YOLO) for a repair",
)
async def queue_image_verification(
    maintenance_job_id: uuid.UUID,
    response: Response,
    org_context: Annotated[OrgContext, Depends(require_permission("maintenance:update"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    payload: RepairImageVerificationRequest | None = None,
):
    ver, queued = await request_image_verification(
        db, maintenance_job_id, org_context.organization_id, org_context.user_id,
        payload or RepairImageVerificationRequest(),
    )
    if not queued:
        response.status_code = status.HTTP_200_OK  # same pair already analysed or in progress
    return ResponseEnvelope(data=build_verification_response(ver))


@router.post(
    "/{maintenance_job_id}/repair-verifications/{verification_id}/review",
    response_model=ResponseEnvelope[RepairVerificationResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Human review of an automated image analysis (confirm, reject or mark unresolved)",
)
async def review_verification(
    maintenance_job_id: uuid.UUID,
    verification_id: uuid.UUID,
    payload: RepairVerificationReviewRequest,
    request: Request,
    org_context: Annotated[OrgContext, Depends(require_permission("maintenance:verify"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    review = await review_image_verification(
        db, maintenance_job_id, verification_id, org_context.organization_id, org_context.user_id, payload,
        request_id=getattr(request.state, "request_id", None),
    )
    return ResponseEnvelope(data=build_verification_response(review))


@router.get(
    "/{maintenance_job_id}/repair-verifications/{verification_id}/image-urls",
    response_model=ResponseEnvelope[SignedImageUrls],
    summary="Short-lived signed URLs for the BEFORE and AFTER images of a verification",
)
async def get_verification_image_urls(
    maintenance_job_id: uuid.UUID,
    verification_id: uuid.UUID,
    org_context: Annotated[OrgContext, Depends(require_permission("maintenance:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    data = await verification_image_urls(db, maintenance_job_id, verification_id, org_context.organization_id)
    return ResponseEnvelope(data=SignedImageUrls(**data))
