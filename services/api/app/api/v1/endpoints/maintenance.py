import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from geoalchemy2.shape import to_shape
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import OrgContext, require_permission
from app.core.database import get_db
from app.models.damage import DamageRecord
from app.models.identity import Organization, OrganizationMembership, Role, User
from app.models.intelligence import RoadHealthSnapshot
from app.models.maintenance import (
    MaintenanceDamageLink,
    MaintenanceJob,
    MaintenanceStatusHistory,
)
from app.models.road import Road, RoadSegment
from app.schemas.common import (
    PaginatedResponseEnvelope,
    PaginationMeta,
    ResponseEnvelope,
    ResponseMeta,
)
from app.schemas.maintenance import (
    MaintenanceDamageLinkCreate,
    MaintenanceDamageLinkResponse,
    MaintenanceJobAssign,
    MaintenanceJobCreate,
    MaintenanceJobResponse,
    MaintenanceJobUpdate,
    MaintenanceStatusHistoryResponse,
    MaintenanceStatusTransition,
)
from app.services.maintenance_service import (
    VALID_TRANSITIONS,
    assign_maintenance_job,
    create_maintenance_job,
    link_damages_to_job,
    transition_job_status,
    update_maintenance_job,
)
from app.services.spatial import wkt_or_geom_to_point

router = APIRouter()


def build_job_response(job: MaintenanceJob, damage_count: int = 0) -> MaintenanceJobResponse:
    lat, lon = None, None
    if job.location is not None:
        try:
            pt = to_shape(job.location)
            lat, lon = pt.y, pt.x
        except (AttributeError, ValueError, TypeError):
            pass

    return MaintenanceJobResponse(
        id=job.id,
        organization_id=job.organization_id,
        road_id=job.road_id,
        road_segment_id=job.road_segment_id,
        created_by_user_id=job.created_by_user_id,
        assigned_to_user_id=job.assigned_to_user_id,
        assigned_to_organization_id=job.assigned_to_organization_id,
        title=job.title,
        description=job.description,
        priority_level=job.priority_level,
        priority_score=float(job.priority_score) if job.priority_score is not None else None,
        priority_factors=job.priority_factors,
        status=job.status,
        due_at=job.due_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        verified_at=job.verified_at,
        completion_notes=job.completion_notes,
        latitude=lat,
        longitude=lon,
        created_at=job.created_at,
        updated_at=job.updated_at,
        damage_count=damage_count,
    )


@router.get(
    "",
    response_model=PaginatedResponseEnvelope[MaintenanceJobResponse],
    summary="List maintenance jobs with filtering and pagination",
)
async def list_maintenance_jobs(
    request: Request,
    org_context: Annotated[OrgContext, Depends(require_permission("maintenance:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    priority: Annotated[str | None, Query()] = None,
    road_id: Annotated[uuid.UUID | None, Query()] = None,
    road_segment_id: Annotated[uuid.UUID | None, Query()] = None,
    assigned_to: Annotated[uuid.UUID | None, Query()] = None,
    from_date: Annotated[datetime | None, Query(alias="from")] = None,
    to_date: Annotated[datetime | None, Query(alias="to")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: Annotated[str, Query()] = "created_at:desc",
):
    query = select(MaintenanceJob).where(MaintenanceJob.organization_id == org_context.organization_id)

    if status_filter:
        query = query.where(MaintenanceJob.status == status_filter.upper())
    if priority:
        query = query.where(MaintenanceJob.priority_level == priority.upper())
    if road_id:
        query = query.where(MaintenanceJob.road_id == road_id)
    if road_segment_id:
        query = query.where(MaintenanceJob.road_segment_id == road_segment_id)
    if assigned_to:
        query = query.where(MaintenanceJob.assigned_to_user_id == assigned_to)
    if from_date:
        query = query.where(MaintenanceJob.created_at >= from_date)
    if to_date:
        query = query.where(MaintenanceJob.created_at <= to_date)

    # Count total
    count_stmt = select(func.count()).select_from(query.subquery())
    total_items = (await db.execute(count_stmt)).scalar() or 0

    # Sorting
    if sort == "due_at:asc":
        query = query.order_by(MaintenanceJob.due_at.asc().nulls_last())
    elif sort == "priority_score:desc":
        query = query.order_by(MaintenanceJob.priority_score.desc().nulls_last())
    else:
        query = query.order_by(desc(MaintenanceJob.created_at))

    # Pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    jobs = list((await db.execute(query)).scalars().all())

    # Count damage links for each job
    job_ids = [j.id for j in jobs]
    damage_counts: dict[uuid.UUID, int] = {}
    if job_ids:
        dmg_c_q = (
            select(MaintenanceDamageLink.maintenance_job_id, func.count(MaintenanceDamageLink.damage_record_id))
            .where(MaintenanceDamageLink.maintenance_job_id.in_(job_ids))
            .group_by(MaintenanceDamageLink.maintenance_job_id)
        )
        counts_res = (await db.execute(dmg_c_q)).all()
        damage_counts = {jid: cnt for jid, cnt in counts_res}

    items = [build_job_response(j, damage_counts.get(j.id, 0)) for j in jobs]
    total_pages = (total_items + page_size - 1) // page_size

    return PaginatedResponseEnvelope(
        data=items,
        meta=PaginationMeta(
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
    response_model=ResponseEnvelope[MaintenanceJobResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create a new maintenance job",
)
async def create_job(
    payload: MaintenanceJobCreate,
    request: Request,
    org_context: Annotated[OrgContext, Depends(require_permission("maintenance:create"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    job = await create_maintenance_job(
        db=db,
        organization_id=org_context.organization_id,
        user_id=org_context.user_id,
        payload=payload,
    )
    return ResponseEnvelope(
        data=build_job_response(job, len(payload.damage_record_ids)),
        meta=ResponseMeta(request_id=getattr(request.state, "request_id", None)),
    )


@router.get(
    "/assignees",
    response_model=ResponseEnvelope[dict[str, Any]],
    summary="Users and contractor organizations a maintenance job can be assigned to",
)
async def list_assignees(
    org_context: Annotated[OrgContext, Depends(require_permission("maintenance:assign"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Only existing records: active members of this organization and active CONTRACTOR organizations."""
    members = (
        await db.execute(
            select(User, Role.code)
            .join(OrganizationMembership, OrganizationMembership.user_id == User.id)
            .join(Role, Role.id == OrganizationMembership.role_id)
            .where(
                OrganizationMembership.organization_id == org_context.organization_id,
                OrganizationMembership.status == "ACTIVE",
                User.is_active.is_(True),
            )
            .order_by(User.full_name)
        )
    ).all()
    contractors = (
        await db.execute(
            select(Organization)
            .where(Organization.organization_type == "CONTRACTOR", Organization.is_active.is_(True))
            .order_by(Organization.name)
        )
    ).scalars().all()
    return ResponseEnvelope(
        data={
            "users": [
                {"id": str(u.id), "full_name": u.full_name, "email": u.email, "role": role} for u, role in members
            ],
            "contractor_organizations": [{"id": str(o.id), "name": o.name, "code": o.code} for o in contractors],
        }
    )


@router.get(
    "/{maintenance_job_id}/context",
    response_model=ResponseEnvelope[dict[str, Any]],
    summary="Job with linked damage, original inspection, road/segment, health and assignment context",
)
async def get_job_context(
    maintenance_job_id: uuid.UUID,
    org_context: Annotated[OrgContext, Depends(require_permission("maintenance:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    job = await db.get(MaintenanceJob, maintenance_job_id)
    if not job or job.organization_id != org_context.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": "Maintenance job was not found."},
        )
    links = (
        await db.execute(
            select(MaintenanceDamageLink)
            .options(selectinload(MaintenanceDamageLink.damage_record).selectinload(DamageRecord.damage_type))
            .where(MaintenanceDamageLink.maintenance_job_id == job.id)
            .order_by(MaintenanceDamageLink.created_at)
        )
    ).scalars().all()
    road = await db.get(Road, job.road_id) if job.road_id else None
    segment = await db.get(RoadSegment, job.road_segment_id) if job.road_segment_id else None
    damages = []
    for link in links:
        d = link.damage_record
        if d is None:
            continue
        coords = wkt_or_geom_to_point(d.location) if d.location is not None else None
        damages.append({
            "id": str(d.id),
            "relationship_type": link.relationship_type,
            "damage_type": d.damage_type.code if d.damage_type else None,
            "severity": d.severity,
            "status": d.status,
            "source_type": d.source_type,
            "confidence": float(d.confidence) if d.confidence is not None else None,
            "observation_count": d.observation_count,
            "inspection_id": str(d.inspection_id) if d.inspection_id else None,
            "source_detection_id": str(d.source_detection_id) if d.source_detection_id else None,
            "road_id": str(d.road_id) if d.road_id else None,
            "road_segment_id": str(d.road_segment_id) if d.road_segment_id else None,
            "location": {"latitude": coords[0], "longitude": coords[1]} if coords else None,
            "detected_at": d.detected_at.isoformat() if d.detected_at else None,
        })

    async def latest_health(segment_id=None, road_id=None):
        conds = [RoadHealthSnapshot.organization_id == job.organization_id]
        if segment_id is not None:
            conds.append(RoadHealthSnapshot.road_segment_id == segment_id)
        else:
            conds += [RoadHealthSnapshot.road_id == road_id, RoadHealthSnapshot.road_segment_id.is_(None)]
        snap = (
            await db.execute(
                select(RoadHealthSnapshot).where(*conds).order_by(desc(RoadHealthSnapshot.calculated_at)).limit(1)
            )
        ).scalar_one_or_none()
        if snap is None:
            return None
        return {
            "health_score": float(snap.health_score) if snap.health_score is not None else None,
            "health_status": snap.health_status,
            "calculation_version": snap.calculation_version,
            "calculated_at": snap.calculated_at.isoformat(),
        }

    assignee = await db.get(User, job.assigned_to_user_id) if job.assigned_to_user_id else None
    contractor = await db.get(Organization, job.assigned_to_organization_id) if job.assigned_to_organization_id else None
    return ResponseEnvelope(
        data={
            "road": {"id": str(road.id), "name": road.name, "road_code": road.road_code,
                     "traffic_volume_class": road.traffic_volume_class} if road else None,
            "segment": {"id": str(segment.id), "name": segment.name, "segment_number": segment.segment_number}
            if segment else None,
            "damages": damages,
            "segment_health": await latest_health(segment_id=segment.id) if segment else None,
            "road_health": await latest_health(road_id=road.id) if road else None,
            "assigned_user": {"id": str(assignee.id), "full_name": assignee.full_name, "email": assignee.email}
            if assignee else None,
            "assigned_organization": {"id": str(contractor.id), "name": contractor.name} if contractor else None,
            "allowed_transitions": VALID_TRANSITIONS.get(job.status, []),
        }
    )


@router.get(
    "/{maintenance_job_id}",
    response_model=ResponseEnvelope[MaintenanceJobResponse],
    summary="Get maintenance job details",
)
async def get_maintenance_job(
    maintenance_job_id: uuid.UUID,
    request: Request,
    org_context: Annotated[OrgContext, Depends(require_permission("maintenance:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    job = await db.get(MaintenanceJob, maintenance_job_id)
    if not job or job.organization_id != org_context.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": "Maintenance job was not found."},
        )

    # Count linked damages
    dmg_c_q = select(func.count()).where(MaintenanceDamageLink.maintenance_job_id == job.id)
    dmg_count = (await db.execute(dmg_c_q)).scalar() or 0

    return ResponseEnvelope(
        data=build_job_response(job, dmg_count),
        meta=ResponseMeta(request_id=getattr(request.state, "request_id", None)),
    )


@router.patch(
    "/{maintenance_job_id}",
    response_model=ResponseEnvelope[MaintenanceJobResponse],
    summary="Update maintenance job attributes",
)
async def update_job(
    maintenance_job_id: uuid.UUID,
    payload: MaintenanceJobUpdate,
    request: Request,
    org_context: Annotated[OrgContext, Depends(require_permission("maintenance:update"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    job = await db.get(MaintenanceJob, maintenance_job_id)
    if not job or job.organization_id != org_context.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": "Maintenance job was not found."},
        )

    updated = await update_maintenance_job(db=db, job=job, payload=payload)
    dmg_c_q = select(func.count()).where(MaintenanceDamageLink.maintenance_job_id == job.id)
    dmg_count = (await db.execute(dmg_c_q)).scalar() or 0

    return ResponseEnvelope(
        data=build_job_response(updated, dmg_count),
        meta=ResponseMeta(request_id=getattr(request.state, "request_id", None)),
    )


@router.post(
    "/{maintenance_job_id}/assign",
    response_model=ResponseEnvelope[MaintenanceJobResponse],
    summary="Assign maintenance job to an officer or contractor organization",
)
async def assign_job(
    maintenance_job_id: uuid.UUID,
    payload: MaintenanceJobAssign,
    request: Request,
    org_context: Annotated[OrgContext, Depends(require_permission("maintenance:assign"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    job = await db.get(MaintenanceJob, maintenance_job_id)
    if not job or job.organization_id != org_context.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": "Maintenance job was not found."},
        )

    assignee_id = payload.assigned_to_user_id or payload.assigned_to
    # Only real assignees: an active member of this organization / an active contractor organization.
    if assignee_id is not None:
        member = (
            await db.execute(
                select(OrganizationMembership.id).where(
                    OrganizationMembership.organization_id == org_context.organization_id,
                    OrganizationMembership.user_id == assignee_id,
                    OrganizationMembership.status == "ACTIVE",
                )
            )
        ).first()
        if member is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_ASSIGNEE", "message": "Assignee is not an active member of this organization."},
            )
    if payload.assigned_to_organization_id is not None:
        contractor = await db.get(Organization, payload.assigned_to_organization_id)
        if contractor is None or not contractor.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_CONTRACTOR", "message": "Contractor organization does not exist or is inactive."},
            )
    assigned_job = await assign_maintenance_job(
        db=db,
        job=job,
        user_id=org_context.user_id,
        assigned_to_user_id=assignee_id,
        assigned_to_organization_id=payload.assigned_to_organization_id,
    )
    dmg_c_q = select(func.count()).where(MaintenanceDamageLink.maintenance_job_id == job.id)
    dmg_count = (await db.execute(dmg_c_q)).scalar() or 0

    return ResponseEnvelope(
        data=build_job_response(assigned_job, dmg_count),
        meta=ResponseMeta(request_id=getattr(request.state, "request_id", None)),
    )


@router.post(
    "/{maintenance_job_id}/status",
    response_model=ResponseEnvelope[MaintenanceJobResponse],
    summary="Execute state machine transition for a maintenance job",
)
async def update_job_status(
    maintenance_job_id: uuid.UUID,
    payload: MaintenanceStatusTransition,
    request: Request,
    org_context: Annotated[OrgContext, Depends(require_permission("maintenance:status_update"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    job = await db.get(MaintenanceJob, maintenance_job_id)
    if not job or job.organization_id != org_context.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": "Maintenance job was not found."},
        )

    notes = payload.notes or payload.reason
    transitioned = await transition_job_status(
        db=db,
        job=job,
        new_status=payload.status,
        user_id=org_context.user_id,
        notes=notes,
    )
    dmg_c_q = select(func.count()).where(MaintenanceDamageLink.maintenance_job_id == job.id)
    dmg_count = (await db.execute(dmg_c_q)).scalar() or 0

    return ResponseEnvelope(
        data=build_job_response(transitioned, dmg_count),
        meta=ResponseMeta(request_id=getattr(request.state, "request_id", None)),
    )


@router.get(
    "/{maintenance_job_id}/history",
    response_model=ResponseEnvelope[list[MaintenanceStatusHistoryResponse]],
    summary="Get chronological status history for a maintenance job",
)
async def get_job_history(
    maintenance_job_id: uuid.UUID,
    request: Request,
    org_context: Annotated[OrgContext, Depends(require_permission("maintenance:view_history"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    job = await db.get(MaintenanceJob, maintenance_job_id)
    if not job or job.organization_id != org_context.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": "Maintenance job was not found."},
        )

    q = (
        select(MaintenanceStatusHistory)
        .where(MaintenanceStatusHistory.maintenance_job_id == job.id)
        .order_by(MaintenanceStatusHistory.changed_at.asc())
    )
    history_records = list((await db.execute(q)).scalars().all())

    items = [
        MaintenanceStatusHistoryResponse(
            id=h.id,
            organization_id=h.organization_id,
            maintenance_job_id=h.maintenance_job_id,
            previous_status=h.previous_status,
            new_status=h.new_status,
            changed_by_user_id=h.changed_by_user_id,
            reason=h.reason,
            changed_at=h.changed_at,
        )
        for h in history_records
    ]
    return ResponseEnvelope(
        data=items,
        meta=ResponseMeta(request_id=getattr(request.state, "request_id", None)),
    )


@router.get(
    "/{maintenance_job_id}/damages",
    response_model=ResponseEnvelope[list[MaintenanceDamageLinkResponse]],
    summary="List damage records linked to a maintenance job",
)
async def get_job_damages(
    maintenance_job_id: uuid.UUID,
    request: Request,
    org_context: Annotated[OrgContext, Depends(require_permission("maintenance:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    job = await db.get(MaintenanceJob, maintenance_job_id)
    if not job or job.organization_id != org_context.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": "Maintenance job was not found."},
        )

    q = (
        select(MaintenanceDamageLink)
        .options(
            selectinload(MaintenanceDamageLink.damage_record).selectinload(DamageRecord.damage_type)
        )
        .where(MaintenanceDamageLink.maintenance_job_id == job.id)
        .order_by(MaintenanceDamageLink.created_at.asc())
    )
    links = list((await db.execute(q)).scalars().all())

    items = []
    for link in links:
        dmg = link.damage_record
        items.append(
            MaintenanceDamageLinkResponse(
                maintenance_job_id=link.maintenance_job_id,
                damage_record_id=link.damage_record_id,
                relationship_type=link.relationship_type,
                created_at=link.created_at,
                severity=dmg.severity if dmg else None,
                status=dmg.status if dmg else None,
                damage_type=dmg.damage_type.code if dmg and dmg.damage_type else None,
            )
        )

    return ResponseEnvelope(
        data=items,
        meta=ResponseMeta(request_id=getattr(request.state, "request_id", None)),
    )


@router.post(
    "/{maintenance_job_id}/damages",
    response_model=ResponseEnvelope[MaintenanceDamageLinkResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Link a confirmed damage record to a maintenance job",
)
async def link_damage(
    maintenance_job_id: uuid.UUID,
    payload: MaintenanceDamageLinkCreate,
    request: Request,
    org_context: Annotated[OrgContext, Depends(require_permission("maintenance:link_damage"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    job = await db.get(MaintenanceJob, maintenance_job_id)
    if not job or job.organization_id != org_context.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": "Maintenance job was not found."},
        )

    link = await link_damages_to_job(
        db=db,
        job=job,
        damage_record_id=payload.damage_record_id,
        relationship_type=payload.relationship_type,
    )

    dmg = await db.get(DamageRecord, payload.damage_record_id)
    return ResponseEnvelope(
        data=MaintenanceDamageLinkResponse(
            maintenance_job_id=link.maintenance_job_id,
            damage_record_id=link.damage_record_id,
            relationship_type=link.relationship_type,
            created_at=link.created_at,
            severity=dmg.severity if dmg else None,
            status=dmg.status if dmg else None,
            damage_type=None,
        ),
        meta=ResponseMeta(request_id=getattr(request.state, "request_id", None)),
    )
