import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import OrgContext, get_current_org_context
from app.core.database import get_db
from app.models.jobs import ProcessingJob
from app.schemas.common import ResponseEnvelope, ResponseMeta
from app.schemas.inspection import ProcessingJobResponseData

router = APIRouter()


@router.get(
    "/{job_id}",
    response_model=ResponseEnvelope[ProcessingJobResponseData],
    summary="Get background processing job status",
)
async def get_processing_job(
    job_id: uuid.UUID,
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(get_current_org_context)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[ProcessingJobResponseData]:
    request_id = getattr(request.state, "request_id", None)

    stmt = select(ProcessingJob).where(ProcessingJob.id == job_id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Processing job not found."},
        )

    if job.organization_id != org_ctx.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ORGANIZATION_ACCESS_DENIED",
                "message": "Job belongs to another organization.",
            },
        )

    data = ProcessingJobResponseData(
        id=job.id,
        job_type=job.job_type,
        entity_type=job.entity_type,
        entity_id=job.entity_id,
        status=job.status,
        priority=job.priority,
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        queued_at=job.queued_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        failed_at=job.failed_at,
        error_code=job.error_code,
        error_message=job.error_message,
    )
    return ResponseEnvelope(
        success=True,
        data=data,
        meta=ResponseMeta(request_id=request_id),
    )
