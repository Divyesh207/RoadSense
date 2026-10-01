import math
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import OrgContext, require_permission
from app.core.database import get_db
from app.models.road import Road, RoadSegment
from app.schemas.auth import MessageResponseData
from app.schemas.common import (
    PaginatedResponseEnvelope,
    PaginationMeta,
    ResponseEnvelope,
    ResponseMeta,
)
from app.schemas.road import (
    LocationMatchRequest,
    LocationMatchResponseData,
    MatchedCandidate,
    RoadCreateRequest,
    RoadResponseData,
    RoadSegmentCreateRequest,
    RoadSegmentResponseData,
    RoadSegmentUpdateRequest,
    RoadUpdateRequest,
)
from app.services.spatial import (
    bbox_intersects_linestring,
    geojson_to_wkt,
    geometry_to_geojson,
    point_to_linestring_distance_m,
)

router = APIRouter()
segments_router = APIRouter()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def build_road_response(road: Road, segment_count: int | None = None) -> RoadResponseData:
    count = segment_count if segment_count is not None else (len(road.segments) if road.segments else 0)
    return RoadResponseData(
        id=road.id,
        organization_id=road.organization_id,
        name=road.name,
        road_code=road.road_code,
        road_type=road.road_type,
        administrative_area=road.administrative_area,
        description=road.description,
        geometry=geometry_to_geojson(road.geometry),
        is_active=road.is_active,
        segment_count=count,
        created_at=road.created_at,
        updated_at=road.updated_at,
    )


def build_segment_response(seg: RoadSegment) -> RoadSegmentResponseData:
    return RoadSegmentResponseData(
        id=seg.id,
        organization_id=seg.organization_id,
        road_id=seg.road_id,
        segment_number=seg.segment_number,
        name=seg.name,
        start_chainage=float(seg.start_chainage) if seg.start_chainage is not None else None,
        end_chainage=float(seg.end_chainage) if seg.end_chainage is not None else None,
        length_meters=float(seg.length_meters) if seg.length_meters is not None else None,
        geometry=geometry_to_geojson(seg.geometry),
        is_active=seg.is_active,
        created_at=seg.created_at,
        updated_at=seg.updated_at,
    )


# --- Road Endpoints ---

@router.get(
    "",
    response_model=PaginatedResponseEnvelope[RoadResponseData],
    summary="List roads for active organization with search and bounding box filtering",
)
async def list_roads(
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("roads:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    search: str | None = None,
    road_type: str | None = None,
    administrative_area: str | None = None,
    is_active: bool = True,
    min_lat: float | None = Query(None, ge=-90.0, le=90.0),
    min_lon: float | None = Query(None, ge=-180.0, le=180.0),
    max_lat: float | None = Query(None, ge=-90.0, le=90.0),
    max_lon: float | None = Query(None, ge=-180.0, le=180.0),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> PaginatedResponseEnvelope[RoadResponseData]:
    request_id = getattr(request.state, "request_id", None)

    # Base query restricted to organization
    stmt = (
        select(Road)
        .where(
            Road.organization_id == org_ctx.organization_id,
            Road.is_active == is_active,
        )
        .options(selectinload(Road.segments))
    )

    if search:
        search_pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            Road.name.ilike(search_pattern) | Road.road_code.ilike(search_pattern)
        )

    if road_type:
        stmt = stmt.where(Road.road_type == road_type)

    if administrative_area:
        stmt = stmt.where(Road.administrative_area.ilike(f"%{administrative_area.strip()}%"))

    result = await db.execute(stmt)
    roads = result.scalars().all()

    # Spatial bounding box filtering if provided
    has_bbox = all(v is not None for v in [min_lat, min_lon, max_lat, max_lon])
    if has_bbox:
        roads = [
            r for r in roads
            if r.geometry and bbox_intersects_linestring(r.geometry, min_lat, min_lon, max_lat, max_lon)  # type: ignore[arg-type]
        ]

    total = len(roads)
    total_pages = max(1, math.ceil(total / page_size))
    start_idx = (page - 1) * page_size
    paged_roads = roads[start_idx : start_idx + page_size]

    data = [build_road_response(r) for r in paged_roads]
    return PaginatedResponseEnvelope(
        success=True,
        data=data,
        meta=PaginationMeta(
            request_id=request_id,
            page=page,
            page_size=page_size,
            total_count=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    )


@router.post(
    "",
    response_model=ResponseEnvelope[RoadResponseData],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new road within active organization",
)
async def create_road(
    payload: RoadCreateRequest,
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("roads:create"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[RoadResponseData]:
    request_id = getattr(request.state, "request_id", None)

    wkt_geom = geojson_to_wkt(payload.geometry)

    road = Road(
        organization_id=org_ctx.organization_id,
        name=payload.name.strip(),
        road_code=payload.road_code.strip() if payload.road_code else None,
        road_type=payload.road_type,
        administrative_area=payload.administrative_area,
        description=payload.description,
        geometry=wkt_geom,
        is_active=True,
    )
    db.add(road)
    await db.commit()
    await db.refresh(road)

    return ResponseEnvelope(
        success=True,
        data=build_road_response(road, segment_count=0),
        meta=ResponseMeta(request_id=request_id),
    )


@router.get(
    "/{road_id}",
    response_model=ResponseEnvelope[RoadResponseData],
    summary="Get road details by ID",
)
async def get_road(
    road_id: uuid.UUID,
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("roads:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[RoadResponseData]:
    request_id = getattr(request.state, "request_id", None)

    stmt = select(Road).where(Road.id == road_id).options(selectinload(Road.segments))
    result = await db.execute(stmt)
    road = result.scalar_one_or_none()

    if road is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Road not found."},
        )

    if road.organization_id != org_ctx.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ORGANIZATION_ACCESS_DENIED",
                "message": "Resource belongs to another organization.",
            },
        )

    return ResponseEnvelope(
        success=True,
        data=build_road_response(road),
        meta=ResponseMeta(request_id=request_id),
    )


@router.patch(
    "/{road_id}",
    response_model=ResponseEnvelope[RoadResponseData],
    summary="Update road metadata and geometry",
)
async def update_road(
    road_id: uuid.UUID,
    payload: RoadUpdateRequest,
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("roads:update"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[RoadResponseData]:
    request_id = getattr(request.state, "request_id", None)

    stmt = select(Road).where(Road.id == road_id).options(selectinload(Road.segments))
    result = await db.execute(stmt)
    road = result.scalar_one_or_none()

    if road is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Road not found."},
        )

    if road.organization_id != org_ctx.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ORGANIZATION_ACCESS_DENIED",
                "message": "Resource belongs to another organization.",
            },
        )

    if payload.name is not None:
        road.name = payload.name.strip()
    if payload.road_code is not None:
        road.road_code = payload.road_code.strip() if payload.road_code else None
    if payload.road_type is not None:
        road.road_type = payload.road_type
    if payload.administrative_area is not None:
        road.administrative_area = payload.administrative_area
    if payload.description is not None:
        road.description = payload.description
    if payload.geometry is not None:
        road.geometry = geojson_to_wkt(payload.geometry)
    if payload.is_active is not None:
        road.is_active = payload.is_active

    road.updated_at = utc_now()
    await db.commit()
    await db.refresh(road)

    return ResponseEnvelope(
        success=True,
        data=build_road_response(road),
        meta=ResponseMeta(request_id=request_id),
    )


@router.delete(
    "/{road_id}",
    response_model=ResponseEnvelope[MessageResponseData],
    summary="Deactivate road (soft delete preserving historical integrity)",
)
async def delete_road(
    road_id: uuid.UUID,
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("roads:delete"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[MessageResponseData]:
    request_id = getattr(request.state, "request_id", None)

    stmt = select(Road).where(Road.id == road_id)
    result = await db.execute(stmt)
    road = result.scalar_one_or_none()

    if road is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Road not found."},
        )

    if road.organization_id != org_ctx.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ORGANIZATION_ACCESS_DENIED",
                "message": "Resource belongs to another organization.",
            },
        )

    road.is_active = False
    road.updated_at = utc_now()
    await db.commit()

    return ResponseEnvelope(
        success=True,
        data=MessageResponseData(message="Road successfully deactivated."),
        meta=ResponseMeta(request_id=request_id),
    )


# --- Segment Endpoints Under /roads/{road_id}/segments ---

@router.get(
    "/{road_id}/segments",
    response_model=ResponseEnvelope[list[RoadSegmentResponseData]],
    summary="List road segments for a specific road",
)
async def list_road_segments(
    road_id: uuid.UUID,
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("road_segments:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[list[RoadSegmentResponseData]]:
    request_id = getattr(request.state, "request_id", None)

    road_stmt = select(Road).where(Road.id == road_id)
    road = (await db.execute(road_stmt)).scalar_one_or_none()

    if road is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Road not found."},
        )

    if road.organization_id != org_ctx.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ORGANIZATION_ACCESS_DENIED",
                "message": "Resource belongs to another organization.",
            },
        )

    stmt = (
        select(RoadSegment)
        .where(
            RoadSegment.road_id == road_id,
            RoadSegment.organization_id == org_ctx.organization_id,
        )
        .order_by(RoadSegment.segment_number.asc())
    )
    result = await db.execute(stmt)
    segments = result.scalars().all()

    data = [build_segment_response(s) for s in segments]
    return ResponseEnvelope(
        success=True,
        data=data,
        meta=ResponseMeta(request_id=request_id),
    )


@router.post(
    "/{road_id}/segments",
    response_model=ResponseEnvelope[RoadSegmentResponseData],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new segment for a road",
)
async def create_road_segment(
    road_id: uuid.UUID,
    payload: RoadSegmentCreateRequest,
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("road_segments:create"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[RoadSegmentResponseData]:
    request_id = getattr(request.state, "request_id", None)

    road_stmt = select(Road).where(Road.id == road_id)
    road = (await db.execute(road_stmt)).scalar_one_or_none()

    if road is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Road not found."},
        )

    if road.organization_id != org_ctx.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ORGANIZATION_ACCESS_DENIED",
                "message": "Resource belongs to another organization.",
            },
        )

    # Check unique segment_number per road
    existing_stmt = select(RoadSegment).where(
        RoadSegment.road_id == road_id,
        RoadSegment.segment_number == payload.segment_number,
    )
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "DUPLICATE_SEGMENT_NUMBER",
                "message": f"Segment number {payload.segment_number} already exists for this road.",
            },
        )

    wkt_geom = geojson_to_wkt(payload.geometry)

    segment = RoadSegment(
        organization_id=org_ctx.organization_id,
        road_id=road_id,
        segment_number=payload.segment_number,
        name=payload.name,
        start_chainage=payload.start_chainage,
        end_chainage=payload.end_chainage,
        length_meters=payload.length_meters,
        geometry=wkt_geom,
        is_active=True,
    )
    db.add(segment)
    await db.commit()
    await db.refresh(segment)

    return ResponseEnvelope(
        success=True,
        data=build_segment_response(segment),
        meta=ResponseMeta(request_id=request_id),
    )


# --- Direct Road Segment Endpoints Under /road-segments/{segment_id} ---

@segments_router.get(
    "/{segment_id}",
    response_model=ResponseEnvelope[RoadSegmentResponseData],
    summary="Get road segment by ID",
)
async def get_road_segment(
    segment_id: uuid.UUID,
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("road_segments:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[RoadSegmentResponseData]:
    request_id = getattr(request.state, "request_id", None)

    stmt = select(RoadSegment).where(RoadSegment.id == segment_id)
    result = await db.execute(stmt)
    segment = result.scalar_one_or_none()

    if segment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Road segment not found."},
        )

    if segment.organization_id != org_ctx.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ORGANIZATION_ACCESS_DENIED",
                "message": "Resource belongs to another organization.",
            },
        )

    return ResponseEnvelope(
        success=True,
        data=build_segment_response(segment),
        meta=ResponseMeta(request_id=request_id),
    )


@segments_router.patch(
    "/{segment_id}",
    response_model=ResponseEnvelope[RoadSegmentResponseData],
    summary="Update road segment by ID",
)
async def update_road_segment(
    segment_id: uuid.UUID,
    payload: RoadSegmentUpdateRequest,
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("road_segments:update"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[RoadSegmentResponseData]:
    request_id = getattr(request.state, "request_id", None)

    stmt = select(RoadSegment).where(RoadSegment.id == segment_id)
    result = await db.execute(stmt)
    segment = result.scalar_one_or_none()

    if segment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Road segment not found."},
        )

    if segment.organization_id != org_ctx.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ORGANIZATION_ACCESS_DENIED",
                "message": "Resource belongs to another organization.",
            },
        )

    if payload.segment_number is not None and payload.segment_number != segment.segment_number:
        conflict_stmt = select(RoadSegment).where(
            RoadSegment.road_id == segment.road_id,
            RoadSegment.segment_number == payload.segment_number,
        )
        conflict = (await db.execute(conflict_stmt)).scalar_one_or_none()
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "DUPLICATE_SEGMENT_NUMBER",
                    "message": f"Segment number {payload.segment_number} already in use.",
                },
            )
        segment.segment_number = payload.segment_number

    if payload.name is not None:
        segment.name = payload.name
    if payload.start_chainage is not None:
        segment.start_chainage = payload.start_chainage
    if payload.end_chainage is not None:
        segment.end_chainage = payload.end_chainage
    if payload.length_meters is not None:
        segment.length_meters = payload.length_meters
    if payload.geometry is not None:
        segment.geometry = geojson_to_wkt(payload.geometry)
    if payload.is_active is not None:
        segment.is_active = payload.is_active

    segment.updated_at = utc_now()
    await db.commit()
    await db.refresh(segment)

    return ResponseEnvelope(
        success=True,
        data=build_segment_response(segment),
        meta=ResponseMeta(request_id=request_id),
    )


@segments_router.delete(
    "/{segment_id}",
    response_model=ResponseEnvelope[MessageResponseData],
    summary="Deactivate road segment (soft delete)",
)
async def delete_road_segment(
    segment_id: uuid.UUID,
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("road_segments:delete"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[MessageResponseData]:
    request_id = getattr(request.state, "request_id", None)

    stmt = select(RoadSegment).where(RoadSegment.id == segment_id)
    result = await db.execute(stmt)
    segment = result.scalar_one_or_none()

    if segment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Road segment not found."},
        )

    if segment.organization_id != org_ctx.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ORGANIZATION_ACCESS_DENIED",
                "message": "Resource belongs to another organization.",
            },
        )

    segment.is_active = False
    segment.updated_at = utc_now()
    await db.commit()

    return ResponseEnvelope(
        success=True,
        data=MessageResponseData(message="Road segment successfully deactivated."),
        meta=ResponseMeta(request_id=request_id),
    )


# --- GIS Location Matching Endpoint ---

@router.post(
    "/match-location",
    response_model=ResponseEnvelope[LocationMatchResponseData],
    summary="Match GPS coordinates to candidate road and road segment with confidence scoring",
)
async def match_location(
    payload: LocationMatchRequest,
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("roads:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[LocationMatchResponseData]:
    request_id = getattr(request.state, "request_id", None)

    # Query active road segments for this organization with road info
    stmt = (
        select(RoadSegment)
        .join(Road, RoadSegment.road_id == Road.id)
        .where(
            RoadSegment.organization_id == org_ctx.organization_id,
            RoadSegment.is_active.is_(True),
            Road.is_active.is_(True),
            RoadSegment.geometry.is_not(None),
        )
        .options(selectinload(RoadSegment.road))
    )
    result = await db.execute(stmt)
    segments = result.scalars().all()

    candidates: list[MatchedCandidate] = []
    for seg in segments:
        dist = point_to_linestring_distance_m(payload.latitude, payload.longitude, seg.geometry)
        if dist is not None and dist <= payload.max_distance_meters:
            if dist <= 10.0:
                confidence = round(1.0 - (dist / 10.0) * 0.1, 3)
            elif dist <= 25.0:
                confidence = round(0.89 - ((dist - 10.0) / 15.0) * 0.19, 3)
            else:
                confidence = round(0.69 - ((dist - 25.0) / (payload.max_distance_meters - 25.0 + 1e-6)) * 0.19, 3)

            is_candidate_uncertain = dist > 25.0
            candidates.append(
                MatchedCandidate(
                    road_id=seg.road_id,
                    road_name=seg.road.name,
                    road_code=seg.road.road_code,
                    segment_id=seg.id,
                    segment_number=seg.segment_number,
                    distance_meters=round(dist, 2),
                    confidence_score=max(0.0, min(1.0, confidence)),
                    is_uncertain=is_candidate_uncertain,
                )
            )

    candidates.sort(key=lambda c: c.distance_meters)

    matched = len(candidates) > 0
    best_match = candidates[0] if matched else None

    is_overall_uncertain = False
    uncertainty_reason = None

    if matched and best_match:
        if best_match.distance_meters > 25.0:
            is_overall_uncertain = True
            uncertainty_reason = "Closest segment exceeds proximity certainty threshold (25m)."
        elif len(candidates) > 1 and (candidates[1].distance_meters - best_match.distance_meters) < 5.0:
            is_overall_uncertain = True
            uncertainty_reason = "Multiple ambiguous road candidates within 5m proximity threshold."
    else:
        uncertainty_reason = "No road segment found within search radius."

    return ResponseEnvelope(
        success=True,
        data=LocationMatchResponseData(
            query_latitude=payload.latitude,
            query_longitude=payload.longitude,
            matched=matched,
            best_match=best_match,
            candidates=candidates,
            is_uncertain=is_overall_uncertain,
            uncertainty_reason=uncertainty_reason if is_overall_uncertain else None,
        ),
        meta=ResponseMeta(request_id=request_id),
    )
