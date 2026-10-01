import asyncio
import logging
import uuid
from typing import Any

from app.core.database import AsyncSessionLocal
from pipelines.media_pipeline import execute_media_pipeline

from worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="tasks.process_inspection_media", bind=True)
def process_inspection_media(
    self,
    job_id: str,
    media_id: str,
    organization_id: str,
    file_path: str | None = None,
    confidence_threshold: float = 0.25,
) -> dict[str, Any]:
    """
    Celery task entrypoint for processing inspection media.
    Runs the complete OpenCV + YOLO + Severity + Geospatial pipeline asynchronously.
    """
    logger.info(f"Worker received process_inspection_media: job={job_id}, media={media_id}")

    async def _run():
        async with AsyncSessionLocal() as session:
            return await execute_media_pipeline(
                db=session,
                job_id=uuid.UUID(job_id),
                media_id=uuid.UUID(media_id),
                organization_id=uuid.UUID(organization_id),
                file_path=file_path,
                confidence_threshold=confidence_threshold,
            )

    return asyncio.run(_run())
