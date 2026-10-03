"""
Repair-verification job: loads the BEFORE and AFTER images of a queued RepairVerification,
runs `verification.repair_analysis` with the deployed detector and persists the outcome.

- Idempotent: a job that is no longer QUEUED is skipped (duplicate/redelivered message).
- Transient storage failures put the job back to QUEUED for a Celery retry until
  max_attempts; permanent failures (missing object, model unavailable) mark it FAILED.
- The automated result never changes the maintenance job state; a human review does.
"""

import logging
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from verification.repair_analysis import ALGORITHM_VERSION, Box, analyze_repair_pair

from inference.detector import BaseDetector
from inference.model_registry import ModelRegistry, TrainedModelRequiredError
from pipelines.media_pipeline import ensure_ai_model, resolve_confidence_threshold

logger = logging.getLogger(__name__)

# read_object(bucket, path) -> bytes. Defaults to the configured storage backend.
ObjectReader = Callable[[str, str], bytes]


class TransientStorageError(RuntimeError):
    pass


class PermanentStorageError(RuntimeError):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _default_reader(bucket: str, path: str) -> bytes:
    from app.services.storage import (
        StorageError,
        StorageObjectNotFoundError,
        get_storage_backend,
    )

    try:
        return get_storage_backend().fetch_to_local_path(bucket, path).read_bytes()
    except StorageObjectNotFoundError as exc:
        raise PermanentStorageError(str(exc)) from exc
    except StorageError as exc:
        raise TransientStorageError(str(exc)) from exc


def detector_fn(detector: BaseDetector, threshold: float) -> Callable[[Any], list[Box]]:
    def detect(image: Any) -> list[Box]:
        result = detector.detect(image, confidence_threshold=threshold)
        return [
            Box(d.damage_type_code, float(d.confidence), d.bbox_x_min, d.bbox_y_min, d.bbox_x_max, d.bbox_y_max)
            for d in result.detections
        ]

    return detect


async def _fail(db: AsyncSession, job: Any, ver: Any, code: str, message: str) -> dict[str, Any]:
    now = utc_now()
    job.status = "FAILED"
    job.completed_at = job.failed_at = now
    job.error_code, job.error_message = code, message
    job.result_metadata = {"status": "FAILED", "error_code": code}
    if ver is not None:
        ver.verification_status = "FAILED"
        ver.error_code, ver.error_message = code, message
        ver.updated_at = now
    await db.commit()
    return {"status": "FAILED", "job_id": str(job.id), "error_code": code, "error_message": message}


async def execute_repair_verification(
    db: AsyncSession,
    job_id: uuid.UUID,
    verification_id: uuid.UUID,
    organization_id: uuid.UUID,
    read_object: ObjectReader | None = None,
    detector: BaseDetector | None = None,
    worker_version: str | None = None,
) -> dict[str, Any]:
    from app.models.ai import AIProcessingRun
    from app.models.inspection import InspectionMedia
    from app.models.jobs import ProcessingJob
    from app.models.repair import RepairEvidence, RepairVerification

    read_object = read_object or _default_reader
    job = (
        await db.execute(
            select(ProcessingJob).where(ProcessingJob.id == job_id, ProcessingJob.organization_id == organization_id)
        )
    ).scalar_one_or_none()
    if job is None:
        raise ValueError(f"ProcessingJob {job_id} not found for org {organization_id}")
    if job.status != "QUEUED":
        logger.warning("Repair verification job %s is %s, not QUEUED; skipping duplicate delivery.", job_id, job.status)
        return {"status": "SKIPPED", "job_id": str(job_id), "job_status": job.status}

    ver = (
        await db.execute(
            select(RepairVerification).where(
                RepairVerification.id == verification_id, RepairVerification.organization_id == organization_id
            )
        )
    ).scalar_one_or_none()
    started = utc_now()
    job.status = "RUNNING"
    job.started_at = started
    job.attempts = (job.attempts or 0) + 1
    if worker_version:
        job.worker_version = worker_version
    if ver is not None:
        ver.verification_status = "PROCESSING"
        ver.updated_at = started
    await db.commit()
    if ver is None:
        return await _fail(db, job, None, "VERIFICATION_NOT_FOUND", f"RepairVerification {verification_id} not found")

    if ver.before_evidence_id:
        before = await db.get(RepairEvidence, ver.before_evidence_id)
        before_source = "REPAIR_EVIDENCE_BEFORE"
    elif ver.before_media_id:
        before = await db.get(InspectionMedia, ver.before_media_id)
        before_source = "INSPECTION_MEDIA"
    else:
        before, before_source = None, None
    after = await db.get(RepairEvidence, ver.after_evidence_id) if ver.after_evidence_id else None
    if before is None or after is None or before.organization_id != organization_id or after.organization_id != organization_id:
        return await _fail(db, job, ver, "EVIDENCE_MISSING", "BEFORE or AFTER image record is missing.")

    try:
        before_bytes = read_object(before.storage_bucket, before.storage_path)
        after_bytes = read_object(after.storage_bucket, after.storage_path)
    except PermanentStorageError as exc:
        return await _fail(db, job, ver, "EVIDENCE_NOT_FOUND", f"Evidence object not found in storage: {exc}")
    except TransientStorageError as exc:
        if job.attempts < job.max_attempts:
            job.status = "QUEUED"
            job.error_code, job.error_message = "STORAGE_UNAVAILABLE", str(exc)
            ver.verification_status = "QUEUED"
            await db.commit()
            logger.warning("Repair verification job %s: storage unavailable, will retry: %s", job_id, exc)
            return {"status": "RETRY", "job_id": str(job_id), "attempts": job.attempts}
        return await _fail(db, job, ver, "STORAGE_UNAVAILABLE", f"Storage unavailable after {job.attempts} attempts: {exc}")

    try:
        detector = detector or ModelRegistry().get_detector()
    except TrainedModelRequiredError as exc:
        return await _fail(db, job, ver, "MODEL_UNAVAILABLE", str(exc))
    threshold = resolve_confidence_threshold(None, detector)

    try:
        analysis = analyze_repair_pair(before_bytes, after_bytes, detector_fn(detector, threshold))
        model_db_id = await ensure_ai_model(db, detector.model_id, detector.model_version)
        now = utc_now()
        run = AIProcessingRun(
            id=uuid.uuid4(),
            organization_id=organization_id,
            processing_job_id=job.id,
            model_id=model_db_id,
            inspection_id=None,
            media_id=None,
            run_type="REPAIR_VERIFICATION",
            configuration_version=ALGORITHM_VERSION,
            confidence_threshold=threshold,
            input_metadata={
                "maintenance_job_id": str(ver.maintenance_job_id),
                "before_source": before_source,
                "before_id": str(before.id),
                "after_evidence_id": str(after.id),
            },
            output_metadata={
                "result": analysis.result,
                "reason_code": analysis.reason_code,
                "inference_backend": detector.backend,
                "before_detection_count": len(analysis.before_detections),
                "after_detection_count": len(analysis.after_detections),
                "residual_detection_count": len(analysis.residual_detections),
            },
            status="COMPLETED",
            started_at=started,
            completed_at=now,
            created_at=now,
        )
        db.add(run)
        findings = analysis.findings()
        findings.update(
            before_source=before_source,
            model={"name": detector.model_id, "version": detector.model_version, "backend": detector.backend,
                   "confidence_threshold": threshold},
        )
        ver.ai_processing_run_id = run.id
        ver.verification_status = "COMPLETED"
        ver.result = analysis.result
        ver.comparison_metrics = analysis.metrics
        ver.findings = findings
        ver.model_name, ver.model_version = detector.model_id, detector.model_version
        ver.algorithm_version = ALGORITHM_VERSION
        ver.ai_confidence = None  # no calibrated probability exists for the decision
        ver.reviewer_notes = f"Automated image analysis: {analysis.result} ({analysis.reason_code}). " + " ".join(analysis.reasons)
        ver.error_code = ver.error_message = None
        ver.updated_at = now
        job.status = "COMPLETED"
        job.completed_at = now
        job.error_code = job.error_message = None
        job.result_metadata = {"status": "COMPLETED", "result": analysis.result, "reason_code": analysis.reason_code,
                               "ai_processing_run_id": str(run.id)}
        await db.commit()
    except Exception as exc:
        await db.rollback()
        logger.exception("Repair verification job %s failed", job_id)
        return await _fail(db, job, ver, "ANALYSIS_ERROR", f"Repair analysis error: {exc!s}")

    logger.info("Repair verification %s: %s (%s)", verification_id, analysis.result, analysis.reason_code)
    return {"status": "COMPLETED", "job_id": str(job_id), "result": analysis.result, "reason_code": analysis.reason_code}
