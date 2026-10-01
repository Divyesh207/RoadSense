import math
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import OrgContext, require_permission
from app.core.database import get_db
from app.models.inspection import Inspection, InspectionMedia
from app.models.jobs import ProcessingJob
from app.models.road import Road, RoadSegment
from app.schemas.common import (
    PaginatedResponseEnvelope,
    PaginationMeta,
    ResponseEnvelope,
    ResponseMeta,
)
from app.schemas.inspection import (
    InspectionCreateRequest,
    InspectionMediaResponseData,
    InspectionMediaSummary,
    InspectionResponseData,
    InspectionUpdateRequest,
    LocationOutput,
    MediaUploadCompleteRequest,
    MediaUploadUrlRequest,
    MediaUploadUrlResponseData,
    ProcessInspectionResponseData,
)
from app.services.spatial import point_to_wkt, wkt_or_geom_to_point

router = APIRouter()


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


from sqlalchemy import inspect as sa_inspect


def get_loaded_rel(instance: Any, attr_name: str, default: Any = None) -> Any:
    try:
        state = sa_inspect(instance)
        if attr_name in state.dict:
            return getattr(instance, attr_name)
    except (AttributeError, KeyError, TypeError):
        return default
    return default


def build_inspection_response(
    insp: Inspection,
    inspector_name: str | None = None,
    road_name: str | None = None,
    segment_number: int | None = None,
    media_list: list[InspectionMedia] | None = None,
) -> InspectionResponseData:
    coords = wkt_or_geom_to_point(insp.location)
    loc_out = (
        LocationOutput(
            latitude=coords[0],
            longitude=coords[1],
            accuracy_m=float(insp.gps_accuracy_meters) if insp.gps_accuracy_meters is not None else None,
        )
        if coords
        else None
    )

    if media_list is not None:
        media = media_list
    else:
        loaded_media = get_loaded_rel(insp, "media")
        media = loaded_media if loaded_media is not None else []

    img_cnt = sum(1 for m in media if getattr(m, "media_type", None) == "IMAGE")
    vid_cnt = sum(1 for m in media if getattr(m, "media_type", None) == "VIDEO")
    summary = InspectionMediaSummary(
        media_count=len(media),
        image_count=img_cnt,
        video_count=vid_cnt,
    )

    if road_name is not None:
        r_name = road_name
    else:
        loaded_road = get_loaded_rel(insp, "road")
        r_name = loaded_road.name if loaded_road else None

    if segment_number is not None:
        s_num = segment_number
    else:
        loaded_seg = get_loaded_rel(insp, "road_segment")
        s_num = loaded_seg.segment_number if loaded_seg else None

    if inspector_name is not None:
        ins_name = inspector_name
    else:
        loaded_ins = get_loaded_rel(insp, "inspector")
        ins_name = loaded_ins.full_name if loaded_ins else None

    return InspectionResponseData(
        id=insp.id,
        organization_id=insp.organization_id,
        inspector_user_id=insp.inspector_user_id,
        inspector_name=ins_name,
        road_id=insp.road_id,
        road_name=r_name,
        road_segment_id=insp.road_segment_id,
        segment_number=s_num,
        status=insp.status,
        source=insp.source,
        captured_at=insp.captured_at,
        submitted_at=insp.submitted_at,
        location=loc_out,
        notes=insp.notes,
        client_inspection_id=insp.client_inspection_id,
        media_summary=summary,
        created_at=insp.created_at,
        updated_at=insp.updated_at,
    )


def build_media_response(media: InspectionMedia) -> InspectionMediaResponseData:
    return InspectionMediaResponseData(
        id=media.id,
        inspection_id=media.inspection_id,
        media_type=media.media_type,
        storage_bucket=media.storage_bucket,
        storage_path=media.storage_path,
        original_filename=media.original_filename,
        mime_type=media.mime_type,
        file_size_bytes=media.file_size_bytes,
        checksum=media.checksum,
        upload_status=media.upload_status,
        duration_seconds=float(media.duration_seconds) if media.duration_seconds is not None else None,
        width_px=media.width_px,
        height_px=media.height_px,
        created_at=media.created_at,
    )


@router.post(
    "",
    response_model=ResponseEnvelope[InspectionResponseData],
    status_code=status.HTTP_201_CREATED,
    summary="Create an inspection record (DRAFT status)",
)
async def create_inspection(
    payload: InspectionCreateRequest,
    request: Request,
    response: Response,
    org_ctx: Annotated[OrgContext, Depends(require_permission("inspections:create"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[InspectionResponseData]:
    request_id = getattr(request.state, "request_id", None)

    # Check road association if provided
    if payload.road_id:
        r_stmt = select(Road).where(
            Road.id == payload.road_id,
            Road.organization_id == org_ctx.organization_id,
        )
        road = (await db.execute(r_stmt)).scalar_one_or_none()
        if not road:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "NOT_FOUND", "message": "Specified road not found in organization."},
            )

    # Check segment association if provided
    if payload.road_segment_id:
        s_stmt = select(RoadSegment).where(
            RoadSegment.id == payload.road_segment_id,
            RoadSegment.organization_id == org_ctx.organization_id,
        )
        seg = (await db.execute(s_stmt)).scalar_one_or_none()
        if not seg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "NOT_FOUND", "message": "Specified road segment not found in organization."},
            )

    # Idempotent offline sync check by client_inspection_id
    if payload.client_id:
        exist_stmt = select(Inspection).where(
            Inspection.organization_id == org_ctx.organization_id,
            Inspection.client_inspection_id == payload.client_id,
        ).options(
            selectinload(Inspection.road),
            selectinload(Inspection.road_segment),
            selectinload(Inspection.media),
            selectinload(Inspection.inspector),
        )
        existing = (await db.execute(exist_stmt)).scalar_one_or_none()
        if existing:
            response.status_code = status.HTTP_200_OK
            return ResponseEnvelope(
                success=True,
                data=build_inspection_response(existing),
                meta=ResponseMeta(request_id=request_id),
            )

    pt_geom = (
        point_to_wkt(payload.location.latitude, payload.location.longitude)
        if payload.location
        else None
    )
    accuracy = payload.location.accuracy_m if payload.location else None

    inspection = Inspection(
        organization_id=org_ctx.organization_id,
        inspector_user_id=org_ctx.membership.user_id,
        road_id=payload.road_id,
        road_segment_id=payload.road_segment_id,
        status="DRAFT",
        source="ANDROID" if payload.client_id else "API",
        captured_at=payload.captured_at or utc_now(),
        location=pt_geom,
        gps_accuracy_meters=accuracy,
        notes=payload.notes,
        client_inspection_id=payload.client_id,
        created_at=utc_now(),
    )
    db.add(inspection)
    await db.commit()
    await db.refresh(inspection)

    return ResponseEnvelope(
        success=True,
        data=build_inspection_response(inspection),
        meta=ResponseMeta(request_id=request_id),
    )


@router.get(
    "",
    response_model=PaginatedResponseEnvelope[InspectionResponseData],
    summary="List inspections with filtering and pagination",
)
async def list_inspections(
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("inspections:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    insp_status: str | None = Query(None, alias="status"),
    inspector_id: uuid.UUID | None = None,
    road_id: uuid.UUID | None = None,
    road_segment_id: uuid.UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> PaginatedResponseEnvelope[InspectionResponseData]:
    request_id = getattr(request.state, "request_id", None)

    stmt = (
        select(Inspection)
        .where(Inspection.organization_id == org_ctx.organization_id)
        .options(
            selectinload(Inspection.road),
            selectinload(Inspection.road_segment),
            selectinload(Inspection.media),
            selectinload(Inspection.inspector),
        )
    )

    if insp_status:
        stmt = stmt.where(Inspection.status == insp_status.upper())
    if inspector_id:
        stmt = stmt.where(Inspection.inspector_user_id == inspector_id)
    if road_id:
        stmt = stmt.where(Inspection.road_id == road_id)
    if road_segment_id:
        stmt = stmt.where(Inspection.road_segment_id == road_segment_id)

    stmt = stmt.order_by(Inspection.created_at.desc())

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_count = (await db.execute(count_stmt)).scalar() or 0
    total_pages = max(1, math.ceil(total_count / page_size))

    # Paginate
    paged_stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(paged_stmt)
    inspections = result.scalars().all()

    data = [build_inspection_response(i) for i in inspections]
    return PaginatedResponseEnvelope(
        success=True,
        data=data,
        meta=PaginationMeta(
            request_id=request_id,
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    )


@router.get(
    "/{inspection_id}",
    response_model=ResponseEnvelope[InspectionResponseData],
    summary="Get full inspection details by ID",
)
async def get_inspection(
    inspection_id: uuid.UUID,
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("inspections:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[InspectionResponseData]:
    request_id = getattr(request.state, "request_id", None)

    stmt = (
        select(Inspection)
        .where(Inspection.id == inspection_id)
        .options(
            selectinload(Inspection.road),
            selectinload(Inspection.road_segment),
            selectinload(Inspection.media),
            selectinload(Inspection.inspector),
        )
    )
    result = await db.execute(stmt)
    insp = result.scalar_one_or_none()

    if insp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Inspection not found."},
        )

    if insp.organization_id != org_ctx.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ORGANIZATION_ACCESS_DENIED",
                "message": "Resource belongs to another organization.",
            },
        )

    return ResponseEnvelope(
        success=True,
        data=build_inspection_response(insp),
        meta=ResponseMeta(request_id=request_id),
    )


@router.patch(
    "/{inspection_id}",
    response_model=ResponseEnvelope[InspectionResponseData],
    summary="Update mutable inspection fields",
)
async def update_inspection(
    inspection_id: uuid.UUID,
    payload: InspectionUpdateRequest,
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("inspections:update"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[InspectionResponseData]:
    request_id = getattr(request.state, "request_id", None)

    stmt = (
        select(Inspection)
        .where(Inspection.id == inspection_id)
        .options(
            selectinload(Inspection.road),
            selectinload(Inspection.road_segment),
            selectinload(Inspection.media),
            selectinload(Inspection.inspector),
        )
    )
    result = await db.execute(stmt)
    insp = result.scalar_one_or_none()

    if insp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Inspection not found."},
        )

    if insp.organization_id != org_ctx.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ORGANIZATION_ACCESS_DENIED",
                "message": "Resource belongs to another organization.",
            },
        )

    if insp.status in ["ANALYZED", "REVIEWED", "COMPLETED"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "INSPECTION_LOCKED",
                "message": f"Inspection in '{insp.status}' state cannot be modified.",
            },
        )

    if payload.notes is not None:
        insp.notes = payload.notes
    if payload.road_id is not None:
        insp.road_id = payload.road_id
    if payload.road_segment_id is not None:
        insp.road_segment_id = payload.road_segment_id

    insp.updated_at = utc_now()
    await db.commit()
    await db.refresh(insp)

    return ResponseEnvelope(
        success=True,
        data=build_inspection_response(insp),
        meta=ResponseMeta(request_id=request_id),
    )


@router.post(
    "/{inspection_id}/submit",
    response_model=ResponseEnvelope[InspectionResponseData],
    summary="Submit inspection (DRAFT/UPLOADING -> SUBMITTED)",
)
async def submit_inspection(
    inspection_id: uuid.UUID,
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("inspections:submit"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[InspectionResponseData]:
    request_id = getattr(request.state, "request_id", None)

    stmt = (
        select(Inspection)
        .where(Inspection.id == inspection_id)
        .options(
            selectinload(Inspection.road),
            selectinload(Inspection.road_segment),
            selectinload(Inspection.media),
            selectinload(Inspection.inspector),
        )
    )
    result = await db.execute(stmt)
    insp = result.scalar_one_or_none()

    if insp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Inspection not found."},
        )

    if insp.organization_id != org_ctx.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ORGANIZATION_ACCESS_DENIED",
                "message": "Resource belongs to another organization.",
            },
        )

    # Valid transitions into SUBMITTED: DRAFT or UPLOADING
    if insp.status not in ["DRAFT", "UPLOADING"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "INVALID_STATE_TRANSITION",
                "message": f"Cannot transition inspection from '{insp.status}' to 'SUBMITTED'.",
            },
        )

    insp.status = "SUBMITTED"
    insp.submitted_at = utc_now()
    insp.updated_at = utc_now()
    await db.commit()
    await db.refresh(insp)

    return ResponseEnvelope(
        success=True,
        data=build_inspection_response(insp),
        meta=ResponseMeta(request_id=request_id),
    )


# --- Media Endpoints ---

@router.post(
    "/{inspection_id}/media/upload-url",
    response_model=ResponseEnvelope[MediaUploadUrlResponseData],
    summary="Request a presigned upload URL for inspection media",
)
async def get_media_upload_url(
    inspection_id: uuid.UUID,
    payload: MediaUploadUrlRequest,
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("inspections:create"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[MediaUploadUrlResponseData]:
    request_id = getattr(request.state, "request_id", None)

    stmt = select(Inspection).where(Inspection.id == inspection_id)
    insp = (await db.execute(stmt)).scalar_one_or_none()

    if insp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Inspection not found."},
        )

    if insp.organization_id != org_ctx.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ORGANIZATION_ACCESS_DENIED",
                "message": "Resource belongs to another organization.",
            },
        )

    file_id = uuid.uuid4()
    clean_filename = payload.filename.replace(" ", "_").replace("/", "_")
    storage_bucket = "inspection-media"
    storage_path = f"inspections/{inspection_id}/{file_id}_{clean_filename}"

    # Generate upload URL (Supabase/S3 object storage signature structure)
    upload_url = f"https://storage.supabase.co/storage/v1/object/{storage_bucket}/{storage_path}?token={secrets_token()}"
    expires_in = 900  # 15 minutes

    return ResponseEnvelope(
        success=True,
        data=MediaUploadUrlResponseData(
            upload_url=upload_url,
            storage_path=storage_path,
            storage_bucket=storage_bucket,
            expires_in=expires_in,
        ),
        meta=ResponseMeta(request_id=request_id),
    )


def secrets_token() -> str:
    import secrets
    return secrets.token_urlsafe(32)


@router.post(
    "/{inspection_id}/media/complete",
    response_model=ResponseEnvelope[InspectionMediaResponseData],
    status_code=status.HTTP_201_CREATED,
    summary="Complete and register media metadata after successful client upload",
)
async def complete_media_upload(
    inspection_id: uuid.UUID,
    payload: MediaUploadCompleteRequest,
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("inspections:create"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[InspectionMediaResponseData]:
    request_id = getattr(request.state, "request_id", None)

    stmt = select(Inspection).where(Inspection.id == inspection_id)
    insp = (await db.execute(stmt)).scalar_one_or_none()

    if insp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Inspection not found."},
        )

    if insp.organization_id != org_ctx.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ORGANIZATION_ACCESS_DENIED",
                "message": "Resource belongs to another organization.",
            },
        )

    media_geom = (
        point_to_wkt(payload.location.latitude, payload.location.longitude)
        if payload.location
        else None
    )

    media = InspectionMedia(
        organization_id=org_ctx.organization_id,
        inspection_id=inspection_id,
        media_type=payload.media_type,
        storage_bucket=payload.storage_bucket,
        storage_path=payload.storage_path,
        original_filename=payload.original_filename,
        mime_type=payload.mime_type,
        file_size_bytes=payload.size_bytes,
        checksum=payload.checksum,
        captured_at=payload.captured_at or utc_now(),
        uploaded_at=utc_now(),
        location=media_geom,
        duration_seconds=payload.duration_seconds,
        width_px=payload.width_px,
        height_px=payload.height_px,
        upload_status="COMPLETED",
        created_at=utc_now(),
    )
    db.add(media)

    # Transition inspection status to UPLOADING if in DRAFT
    if insp.status == "DRAFT":
        insp.status = "UPLOADING"
        insp.updated_at = utc_now()

    await db.commit()
    await db.refresh(media)

    return ResponseEnvelope(
        success=True,
        data=build_media_response(media),
        meta=ResponseMeta(request_id=request_id),
    )


@router.get(
    "/{inspection_id}/media",
    response_model=ResponseEnvelope[list[InspectionMediaResponseData]],
    summary="List all media metadata for an inspection",
)
async def list_inspection_media(
    inspection_id: uuid.UUID,
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("inspection_media:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[list[InspectionMediaResponseData]]:
    request_id = getattr(request.state, "request_id", None)

    stmt = select(Inspection).where(Inspection.id == inspection_id)
    insp = (await db.execute(stmt)).scalar_one_or_none()

    if insp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Inspection not found."},
        )

    if insp.organization_id != org_ctx.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ORGANIZATION_ACCESS_DENIED",
                "message": "Resource belongs to another organization.",
            },
        )

    m_stmt = (
        select(InspectionMedia)
        .where(
            InspectionMedia.inspection_id == inspection_id,
            InspectionMedia.organization_id == org_ctx.organization_id,
        )
        .order_by(InspectionMedia.created_at.asc())
    )
    result = await db.execute(m_stmt)
    media_items = result.scalars().all()

    data = [build_media_response(m) for m in media_items]
    return ResponseEnvelope(
        success=True,
        data=data,
        meta=ResponseMeta(request_id=request_id),
    )


# --- AI Processing Trigger Endpoint ---

@router.post(
    "/{inspection_id}/process",
    response_model=ResponseEnvelope[ProcessInspectionResponseData],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue inspection for asynchronous AI processing",
)
async def process_inspection(
    inspection_id: uuid.UUID,
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("inspections:process"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[ProcessInspectionResponseData]:
    request_id = getattr(request.state, "request_id", None)

    stmt = select(Inspection).where(Inspection.id == inspection_id)
    insp = (await db.execute(stmt)).scalar_one_or_none()

    if insp is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Inspection not found."},
        )

    if insp.organization_id != org_ctx.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "ORGANIZATION_ACCESS_DENIED",
                "message": "Resource belongs to another organization.",
            },
        )

    # Valid state to start processing: SUBMITTED (or retry from PROCESSING_FAILED)
    if insp.status not in ["SUBMITTED", "PROCESSING_FAILED"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "INVALID_STATE_TRANSITION",
                "message": f"Inspection in status '{insp.status}' cannot be queued for processing (must be SUBMITTED).",
            },
        )

    idempotency_key = request.headers.get("Idempotency-Key") or f"insp_proc_{inspection_id}_{utc_now().timestamp()}"

    # Create background processing job
    job = ProcessingJob(
        organization_id=org_ctx.organization_id,
        job_type="INSPECTION_AI_ANALYSIS",
        entity_type="inspections",
        entity_id=inspection_id,
        idempotency_key=idempotency_key,
        status="QUEUED",
        priority=1,
        queued_at=utc_now(),
    )
    db.add(job)

    # Transition inspection status to PROCESSING
    insp.status = "PROCESSING"
    insp.updated_at = utc_now()

    await db.commit()
    await db.refresh(job)

    return ResponseEnvelope(
        success=True,
        data=ProcessInspectionResponseData(
            job_id=job.id,
            status=job.status,
            inspection_id=inspection_id,
        ),
        meta=ResponseMeta(request_id=request_id),
    )
