import uuid
from collections.abc import Sequence
from datetime import datetime, timezone

from fastapi import HTTPException, status
from geoalchemy2 import WKTElement
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.damage import DamageRecord
from app.models.maintenance import (
    MaintenanceDamageLink,
    MaintenanceJob,
    MaintenanceStatusHistory,
)
from app.models.road import Road, RoadSegment
from app.schemas.maintenance import MaintenanceJobCreate, MaintenanceJobUpdate

VALID_TRANSITIONS: dict[str, list[str]] = {
    "OPEN": ["ASSIGNED", "CANCELLED"],
    "ASSIGNED": ["IN_PROGRESS", "OPEN", "CANCELLED"],
    "IN_PROGRESS": ["COMPLETED", "CANCELLED"],
    "COMPLETED": ["VERIFICATION_PENDING", "IN_PROGRESS"],
    "VERIFICATION_PENDING": ["VERIFIED", "REJECTED"],
    "REJECTED": ["IN_PROGRESS", "CANCELLED"],
    "VERIFIED": [],
    "CANCELLED": [],
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def compute_priority_from_damages(damages: Sequence[DamageRecord]) -> tuple[str, float]:
    """Calculate priority level and score from a collection of linked damage records."""
    if not damages:
        return "MEDIUM", 50.0

    severities = [str(d.severity).upper() for d in damages]
    if "CRITICAL" in severities:
        score = min(100.0, 85.0 + (len(damages) * 2.5))
        return "CRITICAL", round(score, 2)
    if "HIGH" in severities:
        score = min(84.0, 65.0 + (len(damages) * 3.0))
        return "HIGH", round(score, 2)
    if "MEDIUM" in severities:
        score = min(64.0, 40.0 + (len(damages) * 3.0))
        return "MEDIUM", round(score, 2)

    score = min(39.0, 20.0 + (len(damages) * 2.0))
    return "LOW", round(score, 2)


async def create_maintenance_job(
    db: AsyncSession,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: MaintenanceJobCreate,
) -> MaintenanceJob:
    """Create a new maintenance job, link requested damages, and initialize status history."""
    # Validate Road & Segment belong to Organization
    if payload.road_id:
        road = await db.get(Road, payload.road_id)
        if not road or road.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "ROAD_NOT_FOUND", "message": "Specified road was not found."},
            )

    if payload.road_segment_id:
        segment = await db.get(RoadSegment, payload.road_segment_id)
        if not segment or segment.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "SEGMENT_NOT_FOUND", "message": "Specified road segment was not found."},
            )

    # Validate linked damages
    linked_damages: list[DamageRecord] = []
    if payload.damage_record_ids:
        dmg_query = select(DamageRecord).where(
            DamageRecord.id.in_(payload.damage_record_ids),
            DamageRecord.organization_id == organization_id,
        )
        linked_damages = list((await db.execute(dmg_query)).scalars().all())
        if len(linked_damages) != len(payload.damage_record_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_DAMAGES",
                    "message": "One or more specified damage records were not found or do not belong to the organization.",
                },
            )

    # Determine priority
    priority_level = payload.priority
    priority_score = payload.priority_score
    if linked_damages and priority_score is None:
        calc_level, calc_score = compute_priority_from_damages(linked_damages)
        if payload.priority == "MEDIUM":  # default
            priority_level = calc_level
        priority_score = calc_score

    # Due date
    due_at = payload.due_at
    if due_at is None and payload.target_date:
        try:
            due_at = datetime.fromisoformat(payload.target_date).replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    # Geometry
    geom = None
    if payload.longitude is not None and payload.latitude is not None:
        geom = WKTElement(f"POINT({payload.longitude} {payload.latitude})", srid=4326)

    job_id = uuid.uuid4()
    now = utc_now()
    initial_status = "ASSIGNED" if payload.assigned_to_user_id else "OPEN"

    job = MaintenanceJob(
        id=job_id,
        organization_id=organization_id,
        road_id=payload.road_id,
        road_segment_id=payload.road_segment_id,
        created_by_user_id=user_id,
        assigned_to_user_id=payload.assigned_to_user_id,
        assigned_to_organization_id=payload.assigned_to_organization_id,
        title=payload.title,
        description=payload.description,
        priority_level=priority_level,
        priority_score=priority_score,
        status=initial_status,
        due_at=due_at,
        location=geom,
        created_at=now,
        updated_at=now,
    )
    db.add(job)

    # Link damages
    for dmg in linked_damages:
        link = MaintenanceDamageLink(
            maintenance_job_id=job_id,
            damage_record_id=dmg.id,
            relationship_type="PRIMARY",
            created_at=now,
        )
        db.add(link)
        if dmg.status in ["DETECTED", "CONFIRMED"]:
            dmg.status = "MAINTENANCE_SCHEDULED"
            dmg.updated_at = now

    # Initial history record
    history = MaintenanceStatusHistory(
        id=uuid.uuid4(),
        organization_id=organization_id,
        maintenance_job_id=job_id,
        previous_status=None,
        new_status=initial_status,
        changed_by_user_id=user_id,
        reason="Initial creation of maintenance job",
        changed_at=now,
    )
    db.add(history)

    await db.commit()
    await db.refresh(job)
    return job


async def transition_job_status(
    db: AsyncSession,
    job: MaintenanceJob,
    new_status: str,
    user_id: uuid.UUID,
    notes: str | None = None,
) -> MaintenanceJob:
    """Transition a maintenance job through the approved state machine."""
    current_status = job.status
    if new_status == current_status:
        return job

    allowed = VALID_TRANSITIONS.get(current_status, [])
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_STATE_TRANSITION",
                "message": f"Cannot transition maintenance job from {current_status} to {new_status}.",
                "allowed_transitions": allowed,
            },
        )

    now = utc_now()
    job.status = new_status
    job.updated_at = now

    if new_status == "IN_PROGRESS" and job.started_at is None:
        job.started_at = now
    elif new_status == "COMPLETED" and job.completed_at is None:
        job.completed_at = now
    elif new_status == "VERIFIED" and job.verified_at is None:
        job.verified_at = now

    if notes:
        job.completion_notes = notes

    # Synchronize linked damage records
    dmg_links_q = (
        select(MaintenanceDamageLink)
        .options(selectinload(MaintenanceDamageLink.damage_record))
        .where(MaintenanceDamageLink.maintenance_job_id == job.id)
    )
    links = (await db.execute(dmg_links_q)).scalars().all()
    for link in links:
        dmg = link.damage_record
        if dmg:
            if new_status == "IN_PROGRESS":
                dmg.status = "IN_PROGRESS"
                dmg.updated_at = now
            elif new_status == "VERIFIED":
                dmg.status = "REPAIRED"
                dmg.updated_at = now

    # Record history
    history = MaintenanceStatusHistory(
        id=uuid.uuid4(),
        organization_id=job.organization_id,
        maintenance_job_id=job.id,
        previous_status=current_status,
        new_status=new_status,
        changed_by_user_id=user_id,
        reason=notes,
        changed_at=now,
    )
    db.add(history)

    await db.commit()
    await db.refresh(job)
    return job


async def assign_maintenance_job(
    db: AsyncSession,
    job: MaintenanceJob,
    user_id: uuid.UUID,
    assigned_to_user_id: uuid.UUID | None,
    assigned_to_organization_id: uuid.UUID | None = None,
) -> MaintenanceJob:
    """Assign maintenance job to a user or contractor organization."""
    job.assigned_to_user_id = assigned_to_user_id
    if assigned_to_organization_id is not None:
        job.assigned_to_organization_id = assigned_to_organization_id
    now = utc_now()
    job.updated_at = now

    # If currently OPEN and assigning to someone, transition to ASSIGNED
    if job.status == "OPEN" and assigned_to_user_id:
        return await transition_job_status(
            db=db,
            job=job,
            new_status="ASSIGNED",
            user_id=user_id,
            notes=f"Job assigned to user {assigned_to_user_id}",
        )

    await db.commit()
    await db.refresh(job)
    return job


async def link_damages_to_job(
    db: AsyncSession,
    job: MaintenanceJob,
    damage_record_id: uuid.UUID,
    relationship_type: str = "PRIMARY",
) -> MaintenanceDamageLink:
    """Link a damage record to an existing maintenance job."""
    dmg = await db.get(DamageRecord, damage_record_id)
    if not dmg or dmg.organization_id != job.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DAMAGE_NOT_FOUND", "message": "Damage record was not found."},
        )

    existing_q = select(MaintenanceDamageLink).where(
        MaintenanceDamageLink.maintenance_job_id == job.id,
        MaintenanceDamageLink.damage_record_id == damage_record_id,
    )
    existing = (await db.execute(existing_q)).scalar_one_or_none()
    if existing:
        return existing

    now = utc_now()
    link = MaintenanceDamageLink(
        maintenance_job_id=job.id,
        damage_record_id=damage_record_id,
        relationship_type=relationship_type,
        created_at=now,
    )
    db.add(link)

    if dmg.status in ["DETECTED", "CONFIRMED"]:
        dmg.status = "MAINTENANCE_SCHEDULED"
        dmg.updated_at = now

    await db.commit()
    return link


async def update_maintenance_job(
    db: AsyncSession,
    job: MaintenanceJob,
    payload: MaintenanceJobUpdate,
) -> MaintenanceJob:
    """Update authorized attributes on a maintenance job."""
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(job, field, value)

    job.updated_at = utc_now()
    await db.commit()
    await db.refresh(job)
    return job
