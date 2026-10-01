import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import OrgContext, require_permission
from app.core.database import get_db
from app.models.damage import DamageRecord
from app.models.intelligence import RoadHealthSnapshot
from app.models.road import Road, RoadSegment
from app.schemas.common import ResponseEnvelope, ResponseMeta
from app.schemas.gis import (
    MapDamageFeature,
    MapRoadFeature,
    MapSegmentFeature,
)
from app.services.spatial import (
    bbox_intersects_linestring,
    geometry_to_geojson,
    wkt_or_geom_to_point,
)

router = APIRouter()


@router.get(
    "/damages",
    response_model=ResponseEnvelope[list[MapDamageFeature]],
    summary="Get spatial damage points for map rendering",
)
async def get_map_damages(
    request: Request,
    org_context: Annotated[OrgContext, Depends(require_permission("damage_records:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    min_lat: Annotated[float | None, Query(ge=-90.0, le=90.0)] = None,
    min_lon: Annotated[float | None, Query(ge=-180.0, le=180.0)] = None,
    max_lat: Annotated[float | None, Query(ge=-90.0, le=90.0)] = None,
    max_lon: Annotated[float | None, Query(ge=-180.0, le=180.0)] = None,
    severity: Annotated[str | None, Query(description="Comma-separated severity list: LOW,MEDIUM,HIGH,CRITICAL")] = None,
    status: Annotated[str | None, Query(description="Comma-separated status list: DETECTED,CONFIRMED,MAINTENANCE_SCHEDULED,REPAIRED,REJECTED")] = None,
    damage_type_id: Annotated[uuid.UUID | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=5000)] = 1000,
):
    query = (
        select(DamageRecord)
        .options(
            selectinload(DamageRecord.damage_type),
            selectinload(DamageRecord.road),
            selectinload(DamageRecord.road_segment),
        )
        .where(DamageRecord.organization_id == org_context.organization_id)
    )

    if severity:
        sev_list = [s.strip().upper() for s in severity.split(",") if s.strip()]
        if sev_list:
            query = query.where(DamageRecord.severity.in_(sev_list))

    if status:
        st_list = [s.strip().upper() for s in status.split(",") if s.strip()]
        if st_list:
            query = query.where(DamageRecord.status.in_(st_list))

    if damage_type_id:
        query = query.where(DamageRecord.damage_type_id == damage_type_id)

    query = query.order_by(desc(DamageRecord.detected_at)).limit(limit)
    result = await db.execute(query)
    records = result.scalars().all()

    features: list[MapDamageFeature] = []
    has_bbox = (
        min_lat is not None and min_lon is not None and max_lat is not None and max_lon is not None
    )

    for record in records:
        coords = wkt_or_geom_to_point(record.location)
        if not coords:
            continue
        lat, lon = coords

        if has_bbox and not (min_lat <= lat <= max_lat and min_lon <= lon <= max_lon):
            continue

        features.append(
            MapDamageFeature(
                id=record.id,
                damage_type=record.damage_type.name if record.damage_type else "UNKNOWN",
                severity=record.severity,
                status=record.status,
                confidence=float(record.confidence) if record.confidence is not None else None,
                latitude=lat,
                longitude=lon,
                road_id=record.road_id,
                road_name=record.road.name if record.road else None,
                road_segment_id=record.road_segment_id,
                segment_number=record.road_segment.segment_number if record.road_segment else None,
                segment_name=record.road_segment.name if record.road_segment else None,
                detected_at=record.detected_at,
            )
        )

    return ResponseEnvelope(
        data=features,
        meta=ResponseMeta(request_id=getattr(request.state, "request_id", None)),
    )


@router.get(
    "/roads",
    response_model=ResponseEnvelope[list[MapRoadFeature]],
    summary="Get roads with geometries and condition summaries for map rendering",
)
async def get_map_roads(
    request: Request,
    org_context: Annotated[OrgContext, Depends(require_permission("roads:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    min_lat: Annotated[float | None, Query(ge=-90.0, le=90.0)] = None,
    min_lon: Annotated[float | None, Query(ge=-180.0, le=180.0)] = None,
    max_lat: Annotated[float | None, Query(ge=-90.0, le=90.0)] = None,
    max_lon: Annotated[float | None, Query(ge=-180.0, le=180.0)] = None,
    road_type: Annotated[str | None, Query()] = None,
):
    query = (
        select(Road)
        .options(selectinload(Road.segments))
        .where(
            Road.organization_id == org_context.organization_id,
            Road.is_active.is_(True),
        )
    )

    if road_type:
        query = query.where(Road.road_type == road_type)

    result = await db.execute(query)
    roads = result.scalars().all()

    has_bbox = (
        min_lat is not None and min_lon is not None and max_lat is not None and max_lon is not None
    )

    features: list[MapRoadFeature] = []

    for road in roads:
        geojson = geometry_to_geojson(road.geometry)
        if not geojson:
            continue

        if has_bbox and not bbox_intersects_linestring(
            road.geometry, min_lat, min_lon, max_lat, max_lon
        ):
            continue

        # Aggregate damages
        dmg_query = select(
            func.count(DamageRecord.id),
            func.count(DamageRecord.id).filter(DamageRecord.severity == "CRITICAL"),
        ).where(
            DamageRecord.organization_id == org_context.organization_id,
            DamageRecord.road_id == road.id,
            DamageRecord.status.in_(["DETECTED", "CONFIRMED", "MAINTENANCE_SCHEDULED", "IN_PROGRESS"]),
        )
        dmg_res = await db.execute(dmg_query)
        total_dmg, crit_dmg = dmg_res.one()

        # Latest health snapshot
        snap_query = (
            select(RoadHealthSnapshot)
            .where(
                RoadHealthSnapshot.organization_id == org_context.organization_id,
                RoadHealthSnapshot.road_id == road.id,
                RoadHealthSnapshot.road_segment_id.is_(None),
            )
            .order_by(desc(RoadHealthSnapshot.calculated_at))
            .limit(1)
        )
        snap = (await db.execute(snap_query)).scalar_one_or_none()

        features.append(
            MapRoadFeature(
                id=road.id,
                name=road.name,
                road_code=road.road_code,
                road_type=road.road_type,
                geometry=geojson,
                length_km=None,
                is_active=road.is_active,
                segment_count=len(road.segments) if road.segments else 0,
                damage_count=total_dmg or 0,
                critical_damage_count=crit_dmg or 0,
                health_score=float(snap.health_score) if snap and snap.health_score is not None else None,
                health_status=snap.health_status if snap else None,
            )
        )

    return ResponseEnvelope(
        data=features,
        meta=ResponseMeta(request_id=getattr(request.state, "request_id", None)),
    )


@router.get(
    "/segments",
    response_model=ResponseEnvelope[list[MapSegmentFeature]],
    summary="Get road segments with geometries and health indicators for map rendering",
)
async def get_map_segments(
    request: Request,
    org_context: Annotated[OrgContext, Depends(require_permission("roads:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    min_lat: Annotated[float | None, Query(ge=-90.0, le=90.0)] = None,
    min_lon: Annotated[float | None, Query(ge=-180.0, le=180.0)] = None,
    max_lat: Annotated[float | None, Query(ge=-90.0, le=90.0)] = None,
    max_lon: Annotated[float | None, Query(ge=-180.0, le=180.0)] = None,
    road_id: Annotated[uuid.UUID | None, Query()] = None,
):
    query = (
        select(RoadSegment)
        .options(selectinload(RoadSegment.road))
        .where(
            RoadSegment.organization_id == org_context.organization_id,
            RoadSegment.is_active.is_(True),
        )
    )

    if road_id:
        query = query.where(RoadSegment.road_id == road_id)

    result = await db.execute(query)
    segments = result.scalars().all()

    has_bbox = (
        min_lat is not None and min_lon is not None and max_lat is not None and max_lon is not None
    )

    features: list[MapSegmentFeature] = []

    for seg in segments:
        geojson = geometry_to_geojson(seg.geometry)
        if not geojson:
            continue

        if has_bbox and not bbox_intersects_linestring(
            seg.geometry, min_lat, min_lon, max_lat, max_lon
        ):
            continue

        dmg_query = select(
            func.count(DamageRecord.id),
            func.count(DamageRecord.id).filter(DamageRecord.severity == "CRITICAL"),
        ).where(
            DamageRecord.organization_id == org_context.organization_id,
            DamageRecord.road_segment_id == seg.id,
            DamageRecord.status.in_(["DETECTED", "CONFIRMED", "MAINTENANCE_SCHEDULED", "IN_PROGRESS"]),
        )
        dmg_res = await db.execute(dmg_query)
        total_dmg, crit_dmg = dmg_res.one()

        # Latest health snapshot
        snap_query = (
            select(RoadHealthSnapshot)
            .where(
                RoadHealthSnapshot.organization_id == org_context.organization_id,
                RoadHealthSnapshot.road_segment_id == seg.id,
            )
            .order_by(desc(RoadHealthSnapshot.calculated_at))
            .limit(1)
        )
        snap = (await db.execute(snap_query)).scalar_one_or_none()

        length_m = (
            float(seg.length_meters)
            if seg.length_meters is not None
            else (
                float((seg.end_chainage - seg.start_chainage) * 1000)
                if seg.start_chainage is not None and seg.end_chainage is not None
                else 100.0
            )
        )

        features.append(
            MapSegmentFeature(
                id=seg.id,
                road_id=seg.road_id,
                road_name=seg.road.name if seg.road else None,
                segment_number=seg.segment_number,
                name=seg.name,
                start_chainage=float(seg.start_chainage) if seg.start_chainage is not None else None,
                end_chainage=float(seg.end_chainage) if seg.end_chainage is not None else None,
                length_meters=length_m,
                geometry=geojson,
                damage_count=total_dmg or 0,
                critical_damage_count=crit_dmg or 0,
                health_score=float(snap.health_score) if snap and snap.health_score is not None else None,
                health_status=snap.health_status if snap else None,
                priority_score=None,
            )
        )

    return ResponseEnvelope(
        data=features,
        meta=ResponseMeta(request_id=getattr(request.state, "request_id", None)),
    )
