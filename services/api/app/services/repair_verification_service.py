"""
Image-based repair verification (Phase 3B), API side.

- `request_image_verification` queues a before/after analysis on the AI worker. It is
  idempotent per (BEFORE image, AFTER image, analysis version) through the
  processing_jobs idempotency key; a FAILED job is re-queued, anything else is reused.
- `review_image_verification` records a human decision as a new HUMAN_REVIEW row that
  references the automated row (which is never modified), applies the final result to
  the maintenance job and its damage, and writes status history and an audit entry.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.task_queue import TaskDispatchError, dispatch_repair_verification
from app.models.ai import AIDetection
from app.models.damage import DamageRecord
from app.models.inspection import InspectionMedia
from app.models.jobs import ProcessingJob
from app.models.maintenance import (
    MaintenanceDamageLink,
    MaintenanceJob,
    MaintenanceStatusHistory,
)
from app.models.repair import RepairEvidence, RepairVerification
from app.schemas.repair import (
    RepairImageVerificationRequest,
    RepairVerificationReviewRequest,
)
from app.services.audit_service import AuditService
from app.services.road_lifecycle import refresh_after_damage_change
from app.services.storage import (
    StorageError,
    get_storage_backend,
    storage_http_exception,
)

JOB_TYPE = "REPAIR_VERIFICATION"
VERIFICATION_TYPE = "AUTOMATED_IMAGE_ANALYSIS"
# Part of the idempotency key: a new analysis version may re-analyse the same pair.
ANALYSIS_KEY_VERSION = "repair-cv-v1.0.1"
REVIEWABLE_JOB_STATES = ("COMPLETED", "VERIFICATION_PENDING")
SIGNED_URL_TTL_SECONDS = 600


def utc_now() -> datetime:
    return datetime.now(UTC)


def _error(code: int, err: str, message: str) -> HTTPException:
    return HTTPException(status_code=code, detail={"code": err, "message": message})


async def _job(db: AsyncSession, job_id: uuid.UUID, org_id: uuid.UUID) -> MaintenanceJob:
    job = await db.get(MaintenanceJob, job_id)
    if job is None or job.organization_id != org_id:
        raise _error(status.HTTP_404_NOT_FOUND, "JOB_NOT_FOUND", "Maintenance job not found.")
    return job


async def _linked_damages(db: AsyncSession, job_id: uuid.UUID, org_id: uuid.UUID) -> list[DamageRecord]:
    stmt = (
        select(DamageRecord)
        .join(MaintenanceDamageLink, MaintenanceDamageLink.damage_record_id == DamageRecord.id)
        .where(MaintenanceDamageLink.maintenance_job_id == job_id, DamageRecord.organization_id == org_id)
    )
    return list((await db.execute(stmt)).scalars().all())


async def _image_evidence(
    db: AsyncSession, job_id: uuid.UUID, org_id: uuid.UUID, evidence_type: str, evidence_id: uuid.UUID | None
) -> RepairEvidence | None:
    stmt = select(RepairEvidence).where(
        RepairEvidence.maintenance_job_id == job_id,
        RepairEvidence.organization_id == org_id,
        RepairEvidence.evidence_type == evidence_type,
        RepairEvidence.media_type == "IMAGE",
    )
    if evidence_id is not None:
        ev = (await db.execute(stmt.where(RepairEvidence.id == evidence_id))).scalar_one_or_none()
        if ev is None:
            raise _error(
                status.HTTP_400_BAD_REQUEST, "INVALID_EVIDENCE",
                f"Evidence {evidence_id} is not {evidence_type} image evidence of this maintenance job.",
            )
        return ev
    return (await db.execute(stmt.order_by(desc(RepairEvidence.created_at)).limit(1))).scalar_one_or_none()


async def _inspection_photo(db: AsyncSession, damages: list[DamageRecord], org_id: uuid.UUID) -> InspectionMedia | None:
    """The photo the documented damage was detected in (via its source detection), else
    the first image of the damage's inspection."""
    for dmg in damages:
        if dmg.source_detection_id:
            det = await db.get(AIDetection, dmg.source_detection_id)
            if det is not None and det.media_id:
                media = await db.get(InspectionMedia, det.media_id)
                if media is not None and media.organization_id == org_id and media.media_type == "IMAGE":
                    return media
    for dmg in damages:
        media = (
            await db.execute(
                select(InspectionMedia)
                .where(
                    InspectionMedia.inspection_id == dmg.inspection_id,
                    InspectionMedia.organization_id == org_id,
                    InspectionMedia.media_type == "IMAGE",
                    InspectionMedia.upload_status == "COMPLETED",
                )
                .order_by(InspectionMedia.created_at)
                .limit(1)
            )
        ).scalar_one_or_none()
        if media is not None:
            return media
    return None


async def _add_history(db, job: MaintenanceJob, new_status: str, user_id: uuid.UUID | None, reason: str) -> None:
    old = job.status
    job.status = new_status
    job.updated_at = utc_now()
    db.add(MaintenanceStatusHistory(
        id=uuid.uuid4(), organization_id=job.organization_id, maintenance_job_id=job.id, previous_status=old,
        new_status=new_status, changed_by_user_id=user_id, reason=reason, changed_at=utc_now(),
    ))


async def _dispatch(db: AsyncSession, pjob: ProcessingJob, ver: RepairVerification, org_id: uuid.UUID) -> None:
    try:
        await run_in_threadpool(dispatch_repair_verification, pjob.id, ver.id, org_id)
    except TaskDispatchError as exc:
        now = utc_now()
        pjob.status, pjob.failed_at, pjob.completed_at = "FAILED", now, now
        pjob.error_code, pjob.error_message = "TASK_DISPATCH_FAILED", f"Could not enqueue verification task: {exc}"
        ver.verification_status, ver.error_code = "FAILED", "TASK_DISPATCH_FAILED"
        ver.error_message = pjob.error_message
        await db.commit()
        raise _error(
            status.HTTP_503_SERVICE_UNAVAILABLE, "TASK_QUEUE_UNAVAILABLE",
            "AI processing queue is unavailable; verification was not started. Retry later.",
        ) from exc


async def request_image_verification(
    db: AsyncSession,
    job_id: uuid.UUID,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: RepairImageVerificationRequest,
) -> tuple[RepairVerification, bool]:
    """Returns (verification, newly_queued)."""
    job = await _job(db, job_id, org_id)
    if job.status not in REVIEWABLE_JOB_STATES:
        raise _error(
            status.HTTP_400_BAD_REQUEST, "INVALID_JOB_STATE",
            f"Repair verification needs a COMPLETED or VERIFICATION_PENDING job (current: {job.status}).",
        )
    after = await _image_evidence(db, job_id, org_id, "AFTER_REPAIR", payload.after_evidence_id)
    if after is None:
        raise _error(status.HTTP_400_BAD_REQUEST, "NO_AFTER_EVIDENCE", "Upload an AFTER_REPAIR image first.")
    before_ev = await _image_evidence(db, job_id, org_id, "BEFORE_REPAIR", payload.before_evidence_id)
    before_media = None
    if before_ev is None:
        before_media = await _inspection_photo(db, await _linked_damages(db, job_id, org_id), org_id)
        if before_media is None:
            raise _error(
                status.HTTP_400_BAD_REQUEST, "NO_BEFORE_IMAGE",
                "No BEFORE_REPAIR image and no inspection photo of the linked damage is available.",
            )
    before_key = f"evidence:{before_ev.id}" if before_ev else f"media:{before_media.id}"
    key = f"{before_key}|after:{after.id}|{ANALYSIS_KEY_VERSION}"

    existing = (
        await db.execute(
            select(ProcessingJob).where(
                ProcessingJob.organization_id == org_id,
                ProcessingJob.job_type == JOB_TYPE,
                ProcessingJob.idempotency_key == key,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        ver = (
            await db.execute(select(RepairVerification).where(RepairVerification.processing_job_id == existing.id))
        ).scalar_one_or_none()
        if ver is not None and existing.status != "FAILED":
            return ver, False
        if ver is not None:  # failed earlier: re-queue the same job and record (no duplicate rows)
            existing.status, existing.attempts = "QUEUED", 0
            existing.error_code = existing.error_message = None
            existing.started_at = existing.completed_at = existing.failed_at = None
            ver.verification_status = "QUEUED"
            ver.error_code = ver.error_message = None
            ver.updated_at = utc_now()
            await db.commit()
            await _dispatch(db, existing, ver, org_id)
            return ver, True

    now = utc_now()
    pjob = existing or ProcessingJob(
        id=uuid.uuid4(), organization_id=org_id, job_type=JOB_TYPE, entity_type="maintenance_job",
        entity_id=job.id, idempotency_key=key, status="QUEUED", max_attempts=3, queued_at=now, created_at=now,
        updated_at=now,
    )
    if existing is None:
        db.add(pjob)
    ver = RepairVerification(
        id=uuid.uuid4(), organization_id=org_id, maintenance_job_id=job.id, verification_status="QUEUED",
        verification_type=VERIFICATION_TYPE, before_evidence_id=before_ev.id if before_ev else None,
        before_media_id=before_media.id if before_media else None, after_evidence_id=after.id,
        processing_job_id=pjob.id, findings={}, created_at=now, updated_at=now,
    )
    db.add(ver)
    if job.status == "COMPLETED":
        await _add_history(db, job, "VERIFICATION_PENDING", user_id, "Automated repair image verification requested.")
    try:
        await db.commit()
    except IntegrityError:
        # A concurrent request created the same job/verification first.
        await db.rollback()
        pj = (
            await db.execute(
                select(ProcessingJob).where(
                    ProcessingJob.organization_id == org_id, ProcessingJob.job_type == JOB_TYPE,
                    ProcessingJob.idempotency_key == key,
                )
            )
        ).scalar_one()
        ver = (
            await db.execute(select(RepairVerification).where(RepairVerification.processing_job_id == pj.id))
        ).scalar_one()
        return ver, False
    await _dispatch(db, pjob, ver, org_id)
    return ver, True


async def review_image_verification(
    db: AsyncSession,
    job_id: uuid.UUID,
    verification_id: uuid.UUID,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: RepairVerificationReviewRequest,
    request_id: str | None = None,
) -> RepairVerification:
    job = await _job(db, job_id, org_id)
    auto = await db.get(RepairVerification, verification_id)
    if auto is None or auto.organization_id != org_id or auto.maintenance_job_id != job.id:
        raise _error(status.HTTP_404_NOT_FOUND, "VERIFICATION_NOT_FOUND", "Repair verification not found.")
    if auto.verification_type != VERIFICATION_TYPE or auto.verification_status != "COMPLETED" or auto.result is None:
        raise _error(
            status.HTTP_400_BAD_REQUEST, "VERIFICATION_NOT_REVIEWABLE",
            "Only a completed automated image analysis can be reviewed.",
        )
    if job.status not in REVIEWABLE_JOB_STATES:
        raise _error(
            status.HTTP_400_BAD_REQUEST, "INVALID_JOB_STATE",
            f"Job in status {job.status} cannot take a verification decision.",
        )
    if payload.decision == "CONFIRMED":
        final = auto.result
    elif payload.decision == "UNRESOLVED":
        final = "UNRESOLVED"
    else:
        final = payload.final_result
        if final == auto.result:
            raise _error(
                status.HTTP_422_UNPROCESSABLE_ENTITY, "REJECTION_MATCHES_RESULT",
                "A rejection must give a different outcome than the automated result.",
            )

    now = utc_now()
    review = RepairVerification(
        id=uuid.uuid4(), organization_id=org_id, maintenance_job_id=job.id, verified_by_user_id=user_id,
        verification_status="REVIEWED", verification_type="HUMAN_REVIEW", result=final,
        previous_result=auto.result, review_decision=payload.decision, reviewed_verification_id=auto.id,
        before_evidence_id=auto.before_evidence_id, before_media_id=auto.before_media_id,
        after_evidence_id=auto.after_evidence_id, model_name=auto.model_name, model_version=auto.model_version,
        algorithm_version=auto.algorithm_version, ai_processing_run_id=auto.ai_processing_run_id,
        findings={"automated_result": auto.result, "review_decision": payload.decision, "final_result": final},
        reviewer_notes=payload.notes, verified_at=now, created_at=now, updated_at=now,
    )
    db.add(review)

    damages = await _linked_damages(db, job.id, org_id)
    changed: list[DamageRecord] = []
    old_status = job.status
    if final == "SUCCESSFUL":
        await _add_history(db, job, "VERIFIED", user_id, payload.notes or "Repair verified after image analysis review.")
        job.verified_at = now
        for dmg in damages:
            if dmg.status != "REJECTED":
                dmg.status, dmg.updated_at = "REPAIRED", now
                changed.append(dmg)
    elif final == "SUBSTANDARD":
        await _add_history(db, job, "REJECTED", user_id, payload.notes or "Repair substandard: rework required.")
        for dmg in damages:
            if dmg.status not in ("REJECTED", "CONFIRMED"):
                dmg.status, dmg.updated_at = "CONFIRMED", now
                changed.append(dmg)
    elif job.status == "COMPLETED":
        await _add_history(db, job, "VERIFICATION_PENDING", user_id, "Verification unresolved: more evidence needed.")

    await AuditService.record_audit_event(
        db, action="REPAIR_VERIFICATION_REVIEWED", entity_type="repair_verification", entity_id=review.id,
        actor_user_id=user_id, organization_id=org_id, request_id=request_id,
        before_data={"automated_verification_id": str(auto.id), "automated_result": auto.result,
                     "job_status": old_status},
        after_data={"review_decision": payload.decision, "final_result": final, "job_status": job.status},
        metadata={"maintenance_job_id": str(job.id), "model_name": auto.model_name,
                  "model_version": auto.model_version, "algorithm_version": auto.algorithm_version},
    )
    await db.commit()
    await db.refresh(review)
    if changed:
        await refresh_after_damage_change(db, org_id, changed)
    return review


async def _signed(bucket: str, path: str) -> str:
    return await run_in_threadpool(
        lambda: get_storage_backend().create_signed_download_url(bucket, path, SIGNED_URL_TTL_SECONDS)
    )


async def evidence_download_url(db: AsyncSession, job_id: uuid.UUID, evidence_id: uuid.UUID, org_id: uuid.UUID) -> str:
    await _job(db, job_id, org_id)
    ev = await db.get(RepairEvidence, evidence_id)
    if ev is None or ev.organization_id != org_id or ev.maintenance_job_id != job_id:
        raise _error(status.HTTP_404_NOT_FOUND, "EVIDENCE_NOT_FOUND", "Repair evidence not found.")
    try:
        return await _signed(ev.storage_bucket, ev.storage_path)
    except StorageError as exc:
        raise storage_http_exception(exc) from exc


async def verification_image_urls(
    db: AsyncSession, job_id: uuid.UUID, verification_id: uuid.UUID, org_id: uuid.UUID
) -> dict[str, Any]:
    await _job(db, job_id, org_id)
    ver = await db.get(RepairVerification, verification_id)
    if ver is None or ver.organization_id != org_id or ver.maintenance_job_id != job_id:
        raise _error(status.HTTP_404_NOT_FOUND, "VERIFICATION_NOT_FOUND", "Repair verification not found.")
    out: dict[str, Any] = {"before_url": None, "before_source": None, "after_url": None,
                           "expires_in_seconds": SIGNED_URL_TTL_SECONDS}
    try:
        if ver.before_evidence_id and (ev := await db.get(RepairEvidence, ver.before_evidence_id)):
            out["before_url"], out["before_source"] = await _signed(ev.storage_bucket, ev.storage_path), "REPAIR_EVIDENCE_BEFORE"
        elif ver.before_media_id and (m := await db.get(InspectionMedia, ver.before_media_id)):
            out["before_url"], out["before_source"] = await _signed(m.storage_bucket, m.storage_path), "INSPECTION_MEDIA"
        if ver.after_evidence_id and (ev := await db.get(RepairEvidence, ver.after_evidence_id)):
            out["after_url"] = await _signed(ev.storage_bucket, ev.storage_path)
    except StorageError as exc:
        raise storage_http_exception(exc) from exc
    return out
