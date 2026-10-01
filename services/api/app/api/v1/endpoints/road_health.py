import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import OrgContext, require_permission
from app.core.database import get_db
from app.models.intelligence import RoadHealthSnapshot
from app.models.road import Road, RoadSegment
from app.schemas.common import (
    PaginatedResponseEnvelope,
    PaginationMeta,
    ResponseEnvelope,
    ResponseMeta,
)
from app.schemas.intelligence import (
    RoadHealthCalculationRequest,
    RoadHealthResponseData,
)
from app.services.health_engine import (
    calculate_road_health,
    calculate_segment_health,
)

road_health_router = APIRouter()
segment_health_router = APIRouter()


def build_health_response(snapshot: RoadHealthSnapshot) -> RoadHealthResponseData:
    return RoadHealthResponseData(
        id=snapshot.id,
        organization_id=snapshot.organization_id,
        road_id=snapshot.road_id,
        road_segment_id=snapshot.road_segment_id,
        health_score=float(snapshot.health_score) if snapshot.health_score is not None else None,
        health_status=snapshot.health_status,
        calculation_version=snapshot.calculation_version,
        input_data_timestamp=snapshot.input_data_timestamp,
        factors=snapshot.factors or {},
        calculation_metadata=snapshot.calculation_metadata,
        calculated_at=snapshot.calculated_at,
        created_at=snapshot.created_at,
    )


# --- Road-level health ---


@road_health_router.get(
    "/{road_id}/health",
    response_model=ResponseEnvelope[RoadHealthResponseData],
    summary="Get current or latest health snapshot for a road",
)
async def get_road_health(
    road_id: uuid.UUID,
    request: Request,
    org_context: Annotated[OrgContext, Depends(require_permission("road_health:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    road = await db.get(Road, road_id)
    if not road or road.organization_id != org_context.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ROAD_NOT_FOUND", "message": "Road was not found."},
        )

    # Check for latest snapshot
    snap_q = (
        select(RoadHealthSnapshot)
        .where(
            RoadHealthSnapshot.organization_id == org_context.organization_id,
            RoadHealthSnapshot.road_id == road.id,
            RoadHealthSnapshot.road_segment_id.is_(None),
        )
        .order_by(desc(RoadHealthSnapshot.calculated_at))
        .limit(1)
    )
    snapshot = (await db.execute(snap_q)).scalar_one_or_none()

    if snapshot is None:
        # Calculate and persist initial snapshot
        snapshot = await calculate_road_health(db, org_context.organization_id, road, persist=True)

    return ResponseEnvelope(
        data=build_health_response(snapshot),
        meta=ResponseMeta(request_id=getattr(request.state, "request_id", None)),
    )


@road_health_router.post(
    "/{road_id}/calculate-health",
    response_model=ResponseEnvelope[RoadHealthResponseData],
    summary="Trigger road health calculation and persist snapshot",
)
async def trigger_road_health_calculation(
    road_id: uuid.UUID,
    request: Request,
    org_context: Annotated[OrgContext, Depends(require_permission("road_health:calculate"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    payload: RoadHealthCalculationRequest | None = None,
):
    road = await db.get(Road, road_id)
    if not road or road.organization_id != org_context.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ROAD_NOT_FOUND", "message": "Road was not found."},
        )

    notes = payload.notes if payload else None
    persist = payload.persist_snapshot if payload else True
    snapshot = await calculate_road_health(db, org_context.organization_id, road, persist=persist, notes=notes)

    return ResponseEnvelope(
        data=build_health_response(snapshot),
        meta=ResponseMeta(request_id=getattr(request.state, "request_id", None)),
    )


# --- Segment-level health ---


@segment_health_router.get(
    "/{segment_id}/health",
    response_model=ResponseEnvelope[RoadHealthResponseData],
    summary="Get current or latest health snapshot for a road segment",
)
async def get_segment_health(
    segment_id: uuid.UUID,
    request: Request,
    org_context: Annotated[OrgContext, Depends(require_permission("road_health:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    segment = await db.get(RoadSegment, segment_id)
    if not segment or segment.organization_id != org_context.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SEGMENT_NOT_FOUND", "message": "Road segment was not found."},
        )

    snap_q = (
        select(RoadHealthSnapshot)
        .where(
            RoadHealthSnapshot.organization_id == org_context.organization_id,
            RoadHealthSnapshot.road_segment_id == segment.id,
        )
        .order_by(desc(RoadHealthSnapshot.calculated_at))
        .limit(1)
    )
    snapshot = (await db.execute(snap_q)).scalar_one_or_none()

    if snapshot is None:
        snapshot = await calculate_segment_health(db, org_context.organization_id, segment, persist=True)

    return ResponseEnvelope(
        data=build_health_response(snapshot),
        meta=ResponseMeta(request_id=getattr(request.state, "request_id", None)),
    )


@segment_health_router.post(
    "/{segment_id}/calculate-health",
    response_model=ResponseEnvelope[RoadHealthResponseData],
    summary="Trigger segment health calculation and persist snapshot",
)
async def trigger_segment_health_calculation(
    segment_id: uuid.UUID,
    request: Request,
    org_context: Annotated[OrgContext, Depends(require_permission("road_health:calculate"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    payload: RoadHealthCalculationRequest | None = None,
):
    segment = await db.get(RoadSegment, segment_id)
    if not segment or segment.organization_id != org_context.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SEGMENT_NOT_FOUND", "message": "Road segment was not found."},
        )

    notes = payload.notes if payload else None
    persist = payload.persist_snapshot if payload else True
    snapshot = await calculate_segment_health(db, org_context.organization_id, segment, persist=persist, notes=notes)

    return ResponseEnvelope(
        data=build_health_response(snapshot),
        meta=ResponseMeta(request_id=getattr(request.state, "request_id", None)),
    )


@segment_health_router.get(
    "/{segment_id}/health/history",
    response_model=PaginatedResponseEnvelope[RoadHealthResponseData],
    summary="Get chronological health history snapshots for a road segment",
)
async def get_segment_health_history(
    segment_id: uuid.UUID,
    request: Request,
    org_context: Annotated[OrgContext, Depends(require_permission("road_health:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    segment = await db.get(RoadSegment, segment_id)
    if not segment or segment.organization_id != org_context.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SEGMENT_NOT_FOUND", "message": "Road segment was not found."},
        )

    count_q = select(func.count(RoadHealthSnapshot.id)).where(
        RoadHealthSnapshot.organization_id == org_context.organization_id,
        RoadHealthSnapshot.road_segment_id == segment.id,
    )
    total_count = (await db.execute(count_q)).scalar() or 0
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0

    history_q = (
        select(RoadHealthSnapshot)
        .where(
            RoadHealthSnapshot.organization_id == org_context.organization_id,
            RoadHealthSnapshot.road_segment_id == segment.id,
        )
        .order_by(desc(RoadHealthSnapshot.calculated_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    snapshots = (await db.execute(history_q)).scalars().all()

    items = [build_health_response(s) for s in snapshots]

    return PaginatedResponseEnvelope(
        data=items,
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
            request_id=getattr(request.state, "request_id", None),
        ),
    )
