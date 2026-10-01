import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import OrgContext, require_permission
from app.core.database import get_db
from app.schemas.common import (
    PaginatedResponseEnvelope,
    PaginationMeta,
    ResponseEnvelope,
)
from app.schemas.recurrence import (
    RecurrenceEvaluateRequest,
    RecurrenceRecordResponse,
    RecurrenceReviewRequest,
    SegmentHistoricalTimelineResponse,
)
from app.services import recurrence_service

router = APIRouter()


@router.get("", response_model=PaginatedResponseEnvelope[RecurrenceRecordResponse])
async def list_recurrences(
    org_context: Annotated[OrgContext, Depends(require_permission("damage_records:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    road_segment_id: Annotated[uuid.UUID | None, Query(description="Filter by road segment ID")] = None,
    status: Annotated[str | None, Query(description="Filter by recurrence status (POTENTIAL, CONFIRMED, DISMISSED)")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
):
    """List recurrence records with spatial and temporal matching metrics."""
    records, total_count = await recurrence_service.list_recurrences(
        db=db,
        organization_id=org_context.organization_id,
        road_segment_id=road_segment_id,
        status_filter=status,
        page=page,
        page_size=page_size,
    )
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
    return PaginatedResponseEnvelope[RecurrenceRecordResponse](
        data=records,
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    )


@router.post("/evaluate", response_model=ResponseEnvelope[list[RecurrenceRecordResponse]])
async def evaluate_recurrence(
    payload: RecurrenceEvaluateRequest,
    org_context: Annotated[OrgContext, Depends(require_permission("maintenance:update"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Run recurrence matching analysis for a specific damage record or all damages across a segment."""
    if payload.new_damage_id:
        created = await recurrence_service.run_recurrence_detection_for_damage(
            db=db,
            new_damage_id=payload.new_damage_id,
            organization_id=org_context.organization_id,
            max_distance_meters=payload.max_distance_meters,
        )
    elif payload.road_segment_id:
        created = await recurrence_service.batch_evaluate_segment_recurrences(
            db=db,
            road_segment_id=payload.road_segment_id,
            organization_id=org_context.organization_id,
            max_distance_meters=payload.max_distance_meters,
        )
    else:
        created = []

    # Format responses
    responses = [
        await recurrence_service.get_recurrence_record(db, c.id, org_context.organization_id)
        for c in created
    ]
    return ResponseEnvelope[list[RecurrenceRecordResponse]](data=responses)


@router.get("/segments/{segment_id}/timeline", response_model=ResponseEnvelope[SegmentHistoricalTimelineResponse])
async def get_segment_history_timeline(
    segment_id: uuid.UUID,
    org_context: Annotated[OrgContext, Depends(require_permission("damage_records:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Retrieve the complete un-overwritten chronological history of a road segment.
    
    Includes damage detections, maintenance job creations, completions, repair verifications,
    and recurrence records.
    """
    timeline = await recurrence_service.get_segment_historical_timeline(
        db=db,
        road_segment_id=segment_id,
        organization_id=org_context.organization_id,
    )
    return ResponseEnvelope[SegmentHistoricalTimelineResponse](data=timeline)


@router.get("/{recurrence_id}", response_model=ResponseEnvelope[RecurrenceRecordResponse])
async def get_recurrence(
    recurrence_id: uuid.UUID,
    org_context: Annotated[OrgContext, Depends(require_permission("damage_records:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get single recurrence record by ID."""
    record = await recurrence_service.get_recurrence_record(
        db=db,
        recurrence_id=recurrence_id,
        organization_id=org_context.organization_id,
    )
    return ResponseEnvelope[RecurrenceRecordResponse](data=record)


@router.post("/{recurrence_id}/review", response_model=ResponseEnvelope[RecurrenceRecordResponse])
async def review_recurrence(
    recurrence_id: uuid.UUID,
    payload: RecurrenceReviewRequest,
    org_context: Annotated[OrgContext, Depends(require_permission("maintenance:verify"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Review and confirm or dismiss a recurrence record (Authority role required)."""
    reviewed = await recurrence_service.review_recurrence_record(
        db=db,
        recurrence_id=recurrence_id,
        organization_id=org_context.organization_id,
        user_id=org_context.user_id,
        new_status=payload.status,
        notes=payload.notes,
    )
    return ResponseEnvelope[RecurrenceRecordResponse](data=reviewed)
