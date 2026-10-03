import math
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import OrgContext, require_permission
from app.core.database import get_db
from app.models.ai import AIDetection, AIProcessingRun, DamageType
from app.models.damage import DamageObservation, DamageRecord, DamageReview
from app.models.inspection import Inspection
from app.schemas.common import (
    PaginatedResponseEnvelope,
    PaginationMeta,
    ResponseEnvelope,
    ResponseMeta,
)
from app.schemas.damage import (
    DamageCreateRequest,
    DamageObservationResponseData,
    DamageRecordResponseData,
    DamageReviewRequest,
    DamageReviewResponseData,
    DamageTypeResponseData,
    DamageUpdateRequest,
)
from app.schemas.inspection import LocationOutput
from app.services.audit_service import AuditService
from app.services.damage_grouping import manual_observation, promote_detection
from app.services.provenance import detection_provenance
from app.services.road_lifecycle import refresh_after_damage_change
from app.services.spatial import point_to_wkt, wkt_or_geom_to_point

router = APIRouter()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# Loads the detector that produced an AI damage record (detection -> run -> model)
SOURCE_MODEL_LOAD = (
    selectinload(DamageRecord.source_detection)
    .selectinload(AIDetection.processing_run)
    .selectinload(AIProcessingRun.model)
)


def get_loaded_rel(instance: Any, attr_name: str, default: Any = None) -> Any:
    try:
        state = sa_inspect(instance)
        if attr_name in state.dict:
            return getattr(instance, attr_name)
    except (AttributeError, KeyError, TypeError):
        return default
    return default


def build_damage_response(
    rec: DamageRecord,
    road_name: str | None = None,
    segment_number: int | None = None,
    reviewed_by_name: str | None = None,
) -> DamageRecordResponseData:
    coords = wkt_or_geom_to_point(rec.location)
    loc_out = (
        LocationOutput(
            latitude=coords[0],
            longitude=coords[1],
        )
        if coords
        else None
    )

    loaded_dt = get_loaded_rel(rec, "damage_type")
    dt_code = loaded_dt.code if loaded_dt else "UNKNOWN"
    dt_name = loaded_dt.name if loaded_dt else "Unknown"

    if road_name is not None:
        r_name = road_name
    else:
        loaded_r = get_loaded_rel(rec, "road")
        r_name = loaded_r.name if loaded_r else None

    if segment_number is not None:
        s_num = segment_number
    else:
        loaded_seg = get_loaded_rel(rec, "road_segment")
        s_num = loaded_seg.segment_number if loaded_seg else None

    if reviewed_by_name is not None:
        rev_name = reviewed_by_name
    else:
        loaded_rev = get_loaded_rel(rec, "reviewed_by")
        rev_name = loaded_rev.full_name if loaded_rev else None

    if rec.source_type == "AI":
        det = get_loaded_rel(rec, "source_detection")
        run = get_loaded_rel(det, "processing_run") if det is not None else None
        prov = detection_provenance(get_loaded_rel(run, "model") if run is not None else None)
    else:
        prov = {"detection_method": "MANUAL", "score_type": None}

    return DamageRecordResponseData(
        id=rec.id,
        organization_id=rec.organization_id,
        inspection_id=rec.inspection_id,
        source_detection_id=rec.source_detection_id,
        road_id=rec.road_id,
        road_name=r_name,
        road_segment_id=rec.road_segment_id,
        segment_number=s_num,
        damage_type_id=rec.damage_type_id,
        damage_type_code=dt_code,
        damage_type_name=dt_name,
        source_type=rec.source_type,
        severity=rec.severity,
        severity_score=float(rec.severity_score) if rec.severity_score is not None else None,
        severity_method_version=rec.severity_method_version,
        location=loc_out,
        status=rec.status,
        confidence=float(rec.confidence) if rec.confidence is not None else None,
        detection_method=prov["detection_method"],
        score_type=prov["score_type"],
        estimated_area_m2=float(rec.estimated_area_m2) if rec.estimated_area_m2 is not None else None,
        observation_count=rec.observation_count or 1,
        last_observed_at=rec.last_observed_at,
        detected_at=rec.detected_at,
        reviewed_at=rec.reviewed_at,
        reviewed_by_user_id=rec.reviewed_by_user_id,
        reviewed_by_name=rev_name,
        notes=rec.notes,
        created_at=rec.created_at,
        updated_at=rec.updated_at,
    )


types_router = APIRouter()


@types_router.get(
    "",
    response_model=ResponseEnvelope[list[DamageTypeResponseData]],
    summary="List all supported damage types",
)
@router.get(
    "/types",
    response_model=ResponseEnvelope[list[DamageTypeResponseData]],
    summary="List all supported damage types",
)
async def list_damage_types(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[list[DamageTypeResponseData]]:
    request_id = getattr(request.state, "request_id", None)
    stmt = select(DamageType).where(DamageType.is_active == True).order_by(DamageType.code)
    types = (await db.execute(stmt)).scalars().all()

    data = [
        DamageTypeResponseData(
            id=t.id,
            code=t.code,
            name=t.name,
            description=t.description,
            is_active=t.is_active,
            created_at=t.created_at,
        )
        for t in types
    ]
    return ResponseEnvelope(success=True, data=data, meta=ResponseMeta(request_id=request_id))


@router.get(
    "",
    response_model=PaginatedResponseEnvelope[DamageRecordResponseData],
    summary="List damage records with filtering and pagination",
)
async def list_damages(
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("damage_records:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    severity: Annotated[str | None, Query()] = None,
    damage_type_id: Annotated[uuid.UUID | None, Query()] = None,
    damage_type_code: Annotated[str | None, Query()] = None,
    road_id: Annotated[uuid.UUID | None, Query()] = None,
    road_segment_id: Annotated[uuid.UUID | None, Query()] = None,
    inspection_id: Annotated[uuid.UUID | None, Query()] = None,
    min_lat: Annotated[float | None, Query()] = None,
    min_lon: Annotated[float | None, Query()] = None,
    max_lat: Annotated[float | None, Query()] = None,
    max_lon: Annotated[float | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponseEnvelope[DamageRecordResponseData]:
    request_id = getattr(request.state, "request_id", None)

    conditions = [DamageRecord.organization_id == org_ctx.organization_id]
    if status_filter:
        conditions.append(DamageRecord.status == status_filter)
    if severity:
        conditions.append(DamageRecord.severity == severity)
    if damage_type_id:
        conditions.append(DamageRecord.damage_type_id == damage_type_id)
    if damage_type_code:
        conditions.append(DamageType.code == damage_type_code)
    if road_id:
        conditions.append(DamageRecord.road_id == road_id)
    if road_segment_id:
        conditions.append(DamageRecord.road_segment_id == road_segment_id)
    if inspection_id:
        conditions.append(DamageRecord.inspection_id == inspection_id)

    count_stmt = (
        select(func.count(DamageRecord.id))
        .join(DamageType, DamageRecord.damage_type_id == DamageType.id)
        .where(*conditions)
    )
    total_items = (await db.execute(count_stmt)).scalar_one()

    offset = (page - 1) * page_size
    stmt = (
        select(DamageRecord)
        .join(DamageType, DamageRecord.damage_type_id == DamageType.id)
        .where(*conditions)
        .options(
            selectinload(DamageRecord.damage_type),
            selectinload(DamageRecord.road),
            selectinload(DamageRecord.road_segment),
            selectinload(DamageRecord.reviewed_by),
            SOURCE_MODEL_LOAD,
        )
        .order_by(DamageRecord.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    records = (await db.execute(stmt)).scalars().all()

    # Spatial bounding box filtering if coordinates provided
    if all(v is not None for v in [min_lat, min_lon, max_lat, max_lon]):
        filtered_records = []
        for r in records:
            coords = wkt_or_geom_to_point(r.location)
            if coords:
                lat, lon = coords
                if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
                    filtered_records.append(r)
        records = filtered_records

    items = [build_damage_response(r) for r in records]
    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 0

    return PaginatedResponseEnvelope(
        success=True,
        data=items,
        meta=PaginationMeta(
            request_id=request_id,
            page=page,
            page_size=page_size,
            total_count=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    )


@router.post(
    "",
    response_model=ResponseEnvelope[DamageRecordResponseData],
    status_code=status.HTTP_201_CREATED,
    summary="Create a manual damage record",
)
async def create_damage_record(
    payload: DamageCreateRequest,
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("damage_records:create"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[DamageRecordResponseData]:
    request_id = getattr(request.state, "request_id", None)

    # Validate inspection
    insp_stmt = select(Inspection).where(
        Inspection.id == payload.inspection_id,
        Inspection.organization_id == org_ctx.organization_id,
    )
    insp = (await db.execute(insp_stmt)).scalar_one_or_none()
    if not insp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Inspection not found in organization."},
        )

    # Validate damage type
    dt_stmt = select(DamageType).where(DamageType.id == payload.damage_type_id)
    dt = (await db.execute(dt_stmt)).scalar_one_or_none()
    if not dt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Damage type not found."},
        )

    pt_geom = (
        point_to_wkt(payload.location.latitude, payload.location.longitude)
        if payload.location
        else insp.location
    )

    record = DamageRecord(
        organization_id=org_ctx.organization_id,
        inspection_id=payload.inspection_id,
        damage_type_id=payload.damage_type_id,
        road_id=payload.road_id or insp.road_id,
        road_segment_id=payload.road_segment_id or insp.road_segment_id,
        source_type="MANUAL",
        severity=payload.severity,
        status="CONFIRMED",
        location=pt_geom,
        confidence=1.0,
        estimated_area_m2=payload.estimated_area_m2,
        detected_at=utc_now(),
        reviewed_at=utc_now(),
        reviewed_by_user_id=org_ctx.membership.user_id,
        notes=payload.notes,
        observation_count=1,
        last_observed_at=utc_now(),
        created_at=utc_now(),
    )
    db.add(record)
    await db.flush()
    db.add(manual_observation(record))
    await db.commit()
    await db.refresh(record)
    await refresh_after_damage_change(db, org_ctx.organization_id, [record])

    # Reload relationships
    rel_stmt = (
        select(DamageRecord)
        .where(DamageRecord.id == record.id)
        .options(
            selectinload(DamageRecord.damage_type),
            selectinload(DamageRecord.road),
            selectinload(DamageRecord.road_segment),
            selectinload(DamageRecord.reviewed_by),
            SOURCE_MODEL_LOAD,
        )
    )
    loaded_rec = (await db.execute(rel_stmt)).scalar_one()

    return ResponseEnvelope(
        success=True,
        data=build_damage_response(loaded_rec),
        meta=ResponseMeta(request_id=request_id),
    )


@router.post(
    "/from-detection/{detection_id}",
    response_model=ResponseEnvelope[DamageRecordResponseData],
    status_code=status.HTTP_201_CREATED,
    summary="Create a candidate canonical damage record from an AI detection",
)
async def create_damage_from_detection(
    detection_id: uuid.UUID,
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("damage_records:create"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[DamageRecordResponseData]:
    request_id = getattr(request.state, "request_id", None)

    # 1. Fetch AI Detection
    det_stmt = (
        select(AIDetection)
        .where(
            AIDetection.id == detection_id,
            AIDetection.organization_id == org_ctx.organization_id,
        )
        .options(
            selectinload(AIDetection.damage_type),
            selectinload(AIDetection.inspection),
        )
    )
    det = (await db.execute(det_stmt)).scalar_one_or_none()
    if not det:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "AI detection not found in organization."},
        )

    # Idempotent per detection; groups onto an open record of the same type within
    # DAMAGE_GROUPING_RADIUS_METERS (GPS drift), otherwise creates a new record.
    result = await promote_detection(db, org_ctx.organization_id, det)
    record = result.record
    if result.action != "ALREADY_PROMOTED":
        await refresh_after_damage_change(db, org_ctx.organization_id, [record])

    rel_stmt = (
        select(DamageRecord)
        .where(DamageRecord.id == record.id)
        .options(
            selectinload(DamageRecord.damage_type),
            selectinload(DamageRecord.road),
            selectinload(DamageRecord.road_segment),
            selectinload(DamageRecord.reviewed_by),
            SOURCE_MODEL_LOAD,
        )
    )
    loaded_rec = (await db.execute(rel_stmt)).scalar_one()

    return ResponseEnvelope(
        success=True,
        data=build_damage_response(loaded_rec),
        meta=ResponseMeta(request_id=request_id),
    )


@router.get(
    "/{damage_id}",
    response_model=ResponseEnvelope[DamageRecordResponseData],
    summary="Get single damage record details",
)
async def get_damage_record(
    damage_id: uuid.UUID,
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("damage_records:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[DamageRecordResponseData]:
    request_id = getattr(request.state, "request_id", None)
    stmt = (
        select(DamageRecord)
        .where(
            DamageRecord.id == damage_id,
            DamageRecord.organization_id == org_ctx.organization_id,
        )
        .options(
            selectinload(DamageRecord.damage_type),
            selectinload(DamageRecord.road),
            selectinload(DamageRecord.road_segment),
            selectinload(DamageRecord.reviewed_by),
            SOURCE_MODEL_LOAD,
        )
    )
    record = (await db.execute(stmt)).scalar_one_or_none()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Damage record not found."},
        )

    return ResponseEnvelope(
        success=True,
        data=build_damage_response(record),
        meta=ResponseMeta(request_id=request_id),
    )


@router.patch(
    "/{damage_id}",
    response_model=ResponseEnvelope[DamageRecordResponseData],
    summary="Update mutable damage record fields",
)
async def update_damage_record(
    damage_id: uuid.UUID,
    payload: DamageUpdateRequest,
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("damage_records:update"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[DamageRecordResponseData]:
    request_id = getattr(request.state, "request_id", None)
    stmt = (
        select(DamageRecord)
        .where(
            DamageRecord.id == damage_id,
            DamageRecord.organization_id == org_ctx.organization_id,
        )
        .options(
            selectinload(DamageRecord.damage_type),
            selectinload(DamageRecord.road),
            selectinload(DamageRecord.road_segment),
            selectinload(DamageRecord.reviewed_by),
            SOURCE_MODEL_LOAD,
        )
    )
    record = (await db.execute(stmt)).scalar_one_or_none()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Damage record not found."},
        )

    if payload.damage_type_id:
        dt = (await db.execute(select(DamageType).where(DamageType.id == payload.damage_type_id))).scalar_one_or_none()
        if not dt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "NOT_FOUND", "message": "Damage type not found."},
            )
        record.damage_type_id = payload.damage_type_id

    if payload.severity:
        record.severity = payload.severity
    if payload.status:
        record.status = payload.status
    if payload.estimated_area_m2 is not None:
        record.estimated_area_m2 = payload.estimated_area_m2
    if payload.notes is not None:
        record.notes = payload.notes

    record.updated_at = utc_now()
    await db.commit()
    await db.refresh(record)
    await refresh_after_damage_change(db, org_ctx.organization_id, [record])

    return ResponseEnvelope(
        success=True,
        data=build_damage_response(record),
        meta=ResponseMeta(request_id=request_id),
    )


@router.post(
    "/{damage_id}/review",
    response_model=ResponseEnvelope[DamageRecordResponseData],
    summary="Perform human review of a candidate damage record",
)
async def review_damage_record(
    damage_id: uuid.UUID,
    payload: DamageReviewRequest,
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("damage_records:review"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[DamageRecordResponseData]:
    request_id = getattr(request.state, "request_id", None)
    stmt = (
        select(DamageRecord)
        .where(
            DamageRecord.id == damage_id,
            DamageRecord.organization_id == org_ctx.organization_id,
        )
        .options(
            selectinload(DamageRecord.damage_type),
            selectinload(DamageRecord.road),
            selectinload(DamageRecord.road_segment),
            selectinload(DamageRecord.reviewed_by),
            SOURCE_MODEL_LOAD,
        )
    )
    record = (await db.execute(stmt)).scalar_one_or_none()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Damage record not found."},
        )

    reviewer_id = org_ctx.membership.user_id
    now = utc_now()

    orig_type_id = record.damage_type_id
    orig_sev = record.severity
    orig_conf = record.confidence

    new_type_id = payload.damage_type_id if payload.damage_type_id else orig_type_id
    new_sev = payload.severity if payload.severity else orig_sev

    if payload.damage_type_id:
        dt = (await db.execute(select(DamageType).where(DamageType.id == payload.damage_type_id))).scalar_one_or_none()
        if not dt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "NOT_FOUND", "message": "Specified replacement damage type not found."},
            )

    # Create immutable review audit entry
    review = DamageReview(
        organization_id=org_ctx.organization_id,
        damage_record_id=record.id,
        reviewer_user_id=reviewer_id,
        review_status=payload.decision,
        original_damage_type_id=orig_type_id,
        reviewed_damage_type_id=new_type_id,
        original_severity=orig_sev,
        reviewed_severity=new_sev,
        original_confidence=orig_conf,
        review_notes=payload.notes,
        reviewed_at=now,
        created_at=now,
    )
    db.add(review)

    # Update canonical damage record
    record.status = payload.decision  # "CONFIRMED" or "REJECTED"
    record.damage_type_id = new_type_id
    record.severity = new_sev
    record.reviewed_at = now
    record.reviewed_by_user_id = reviewer_id
    if payload.notes:
        record.notes = (f"{record.notes}\n[Review]: {payload.notes}").strip() if record.notes else payload.notes
    record.updated_at = now

    await AuditService.record_audit_event(
        db=db,
        action=f"DAMAGE_{payload.decision}",
        entity_type="damage_record",
        entity_id=record.id,
        actor_user_id=reviewer_id,
        organization_id=org_ctx.organization_id,
        request_id=request_id,
        before_data={"status": record.status, "severity": orig_sev},
        after_data={"status": payload.decision, "severity": new_sev, "decision": payload.decision},
    )

    await db.commit()
    await db.refresh(record)
    await refresh_after_damage_change(db, org_ctx.organization_id, [record])

    # Reload relationships for response
    rel_stmt = (
        select(DamageRecord)
        .where(DamageRecord.id == record.id)
        .options(
            selectinload(DamageRecord.damage_type),
            selectinload(DamageRecord.road),
            selectinload(DamageRecord.road_segment),
            selectinload(DamageRecord.reviewed_by),
            SOURCE_MODEL_LOAD,
        )
    )
    loaded_rec = (await db.execute(rel_stmt)).scalar_one()

    return ResponseEnvelope(
        success=True,
        data=build_damage_response(loaded_rec),
        meta=ResponseMeta(request_id=request_id),
    )


@router.get(
    "/{damage_id}/reviews",
    response_model=ResponseEnvelope[list[DamageReviewResponseData]],
    summary="Get review history for a damage record",
)
async def get_damage_reviews(
    damage_id: uuid.UUID,
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("damage_records:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[list[DamageReviewResponseData]]:
    request_id = getattr(request.state, "request_id", None)
    # Validate damage record belongs to org
    dmg_stmt = select(DamageRecord.id).where(
        DamageRecord.id == damage_id,
        DamageRecord.organization_id == org_ctx.organization_id,
    )
    exists = (await db.execute(dmg_stmt)).scalar_one_or_none()
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Damage record not found."},
        )

    stmt = (
        select(DamageReview)
        .where(
            DamageReview.damage_record_id == damage_id,
            DamageReview.organization_id == org_ctx.organization_id,
        )
        .options(selectinload(DamageReview.reviewer))
        .order_by(DamageReview.reviewed_at.desc())
    )
    reviews = (await db.execute(stmt)).scalars().all()

    data = [
        DamageReviewResponseData(
            id=r.id,
            damage_record_id=r.damage_record_id,
            reviewer_user_id=r.reviewer_user_id,
            reviewer_name=r.reviewer.full_name if r.reviewer else None,
            review_status=r.review_status,
            original_damage_type_id=r.original_damage_type_id,
            reviewed_damage_type_id=r.reviewed_damage_type_id,
            original_severity=r.original_severity,
            reviewed_severity=r.reviewed_severity,
            original_confidence=float(r.original_confidence) if r.original_confidence is not None else None,
            review_notes=r.review_notes,
            reviewed_at=r.reviewed_at,
        )
        for r in reviews
    ]

    return ResponseEnvelope(
        success=True,
        data=data,
        meta=ResponseMeta(request_id=request_id),
    )


@router.get(
    "/{damage_id}/observations",
    response_model=ResponseEnvelope[list[DamageObservationResponseData]],
    summary="List the inspection sightings (inspection -> media -> detection) grouped into a damage record",
)
async def list_damage_observations(
    damage_id: uuid.UUID,
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("damage_records:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[list[DamageObservationResponseData]]:
    request_id = getattr(request.state, "request_id", None)
    record = (
        await db.execute(
            select(DamageRecord.id).where(
                DamageRecord.id == damage_id, DamageRecord.organization_id == org_ctx.organization_id
            )
        )
    ).scalar_one_or_none()
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Damage record not found."},
        )
    rows = (
        await db.execute(
            select(DamageObservation)
            .where(
                DamageObservation.damage_record_id == damage_id,
                DamageObservation.organization_id == org_ctx.organization_id,
            )
            .order_by(DamageObservation.observed_at)
        )
    ).scalars().all()
    data = []
    for o in rows:
        coords = wkt_or_geom_to_point(o.location)
        data.append(
            DamageObservationResponseData(
                id=o.id,
                damage_record_id=o.damage_record_id,
                detection_id=o.detection_id,
                inspection_id=o.inspection_id,
                media_id=o.media_id,
                match_method=o.match_method,
                distance_meters=float(o.distance_meters) if o.distance_meters is not None else None,
                location=LocationOutput(latitude=coords[0], longitude=coords[1]) if coords else None,
                observed_at=o.observed_at,
            )
        )
    return ResponseEnvelope(success=True, data=data, meta=ResponseMeta(request_id=request_id))
