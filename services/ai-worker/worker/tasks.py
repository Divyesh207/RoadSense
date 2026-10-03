import asyncio
import logging
import uuid
from typing import Any

from pipelines.media_pipeline import execute_inspection_pipeline, execute_media_pipeline
from pipelines.repair_pipeline import execute_repair_verification
from worker.celery_app import celery_app
from worker.db import WorkerSessionLocal

logger = logging.getLogger(__name__)

WORKER_VERSION = "road-ai-worker/1.0.0"


def _jsonable(result: dict[str, Any]) -> dict[str, Any]:
    """Celery's JSON serializer cannot encode UUIDs."""
    out: dict[str, Any] = {}
    for key, value in result.items():
        if isinstance(value, uuid.UUID):
            out[key] = str(value)
        elif isinstance(value, list):
            out[key] = [str(v) if isinstance(v, uuid.UUID) else v for v in value]
        else:
            out[key] = value
    return out


@celery_app.task(name="tasks.process_inspection", bind=True)
def process_inspection(
    self,
    job_id: str,
    inspection_id: str,
    organization_id: str,
    confidence_threshold: float | None = None,
) -> dict[str, Any]:
    """
    Entry point published by the API (POST /inspections/{id}/process).
    Analyzes all completed media of the inspection under the given ProcessingJob.
    """
    logger.info("Worker received process_inspection: job=%s inspection=%s", job_id, inspection_id)

    async def _run() -> dict[str, Any]:
        async with WorkerSessionLocal() as session:
            return await execute_inspection_pipeline(
                db=session,
                job_id=uuid.UUID(job_id),
                inspection_id=uuid.UUID(inspection_id),
                organization_id=uuid.UUID(organization_id),
                confidence_threshold=confidence_threshold,
                worker_version=WORKER_VERSION,
            )

    return _jsonable(asyncio.run(_run()))


@celery_app.task(name="tasks.process_inspection_media", bind=True)
def process_inspection_media(
    self,
    job_id: str,
    media_id: str,
    organization_id: str,
    file_path: str | None = None,
    confidence_threshold: float | None = None,
) -> dict[str, Any]:
    """
    Single-media entry point (reprocessing one media item under its own job).
    Runs the complete OpenCV/YOLO + Severity + Geospatial pipeline asynchronously.
    """
    logger.info("Worker received process_inspection_media: job=%s media=%s", job_id, media_id)

    async def _run() -> dict[str, Any]:
        async with WorkerSessionLocal() as session:
            return await execute_media_pipeline(
                db=session,
                job_id=uuid.UUID(job_id),
                media_id=uuid.UUID(media_id),
                organization_id=uuid.UUID(organization_id),
                file_path=file_path,
                confidence_threshold=confidence_threshold,
            )

    return _jsonable(asyncio.run(_run()))


@celery_app.task(name="tasks.verify_repair", bind=True, max_retries=3)
def verify_repair(self, job_id: str, verification_id: str, organization_id: str) -> dict[str, Any]:
    """Before/after repair image analysis (published by POST /maintenance-jobs/{id}/repair-verifications).
    Transient storage failures re-queue the job and retry; the job row records every attempt."""
    logger.info("Worker received verify_repair: job=%s verification=%s", job_id, verification_id)

    async def _run() -> dict[str, Any]:
        async with WorkerSessionLocal() as session:
            return await execute_repair_verification(
                db=session,
                job_id=uuid.UUID(job_id),
                verification_id=uuid.UUID(verification_id),
                organization_id=uuid.UUID(organization_id),
                worker_version=WORKER_VERSION,
            )

    result = asyncio.run(_run())
    if result.get("status") == "RETRY":
        raise self.retry(countdown=15)
    return result
