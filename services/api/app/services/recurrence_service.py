import math
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from geoalchemy2.shape import to_shape
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.damage import DamageRecord
from app.models.history import RecurrenceRecord
from app.models.maintenance import MaintenanceDamageLink, MaintenanceJob
from app.models.repair import RepairVerification
from app.models.road import RoadSegment
from app.schemas.recurrence import (
    DamageSummaryItem,
    RecurrenceRecordResponse,
    SegmentHistoricalTimelineResponse,
    SegmentTimelineEvent,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(dt: datetime | None) -> datetime:
    if dt is None:
        return datetime.min.replace(tzinfo=timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def get_coords_from_geom(geom: Any) -> tuple[float, float] | None:
    if geom is None:
        return None
    try:
        pt = to_shape(geom)
        return pt.y, pt.x  # lat, lon
    except (AttributeError, ValueError, TypeError):
        return None


async def run_recurrence_detection_for_damage(
    db: AsyncSession,
    new_damage_id: uuid.UUID,
    organization_id: uuid.UUID,
    max_distance_meters: float = 30.0,
) -> list[RecurrenceRecord]:
    """Evaluates whether a newly recorded damage is a recurrence of a previous repaired/maintained defect."""
    new_dmg = await db.get(DamageRecord, new_damage_id)
    if not new_dmg or new_dmg.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DAMAGE_NOT_FOUND", "message": "Damage record not found."},
        )

    new_coords = get_coords_from_geom(new_dmg.location)
    if not new_coords:
        return []

    new_lat, new_lon = new_coords
    new_timestamp = new_dmg.detected_at or new_dmg.created_at

    # Find historical candidates on the same segment or organization
    query = (
        select(DamageRecord)
        .where(
            DamageRecord.organization_id == organization_id,
            DamageRecord.id != new_dmg.id,
            DamageRecord.created_at < new_timestamp,
        )
    )
    if new_dmg.road_segment_id:
        query = query.where(DamageRecord.road_segment_id == new_dmg.road_segment_id)

    historical_damages = list((await db.execute(query)).scalars().all())

    created_records: list[RecurrenceRecord] = []
    now = utc_now()

    for hist in historical_damages:
        hist_coords = get_coords_from_geom(hist.location)
        if not hist_coords:
            continue

        hist_lat, hist_lon = hist_coords
        dist = haversine_distance_meters(new_lat, new_lon, hist_lat, hist_lon)

        if dist <= max_distance_meters:
            # Check if recurrence record already exists
            existing_check = await db.execute(
                select(RecurrenceRecord).where(
                    RecurrenceRecord.historical_damage_id == hist.id,
                    RecurrenceRecord.new_damage_id == new_dmg.id,
                )
            )
            if existing_check.scalar_one_or_none():
                continue

            hist_timestamp = hist.detected_at or hist.created_at
            temporal_days = max(1, (ensure_utc(new_timestamp) - ensure_utc(hist_timestamp)).days)

            # Similarity: type match gives 1.0, otherwise 0.5
            type_similarity = 1.0 if hist.damage_type_id == new_dmg.damage_type_id else 0.5
            dist_score = max(0.0, 1.0 - (dist / max_distance_meters))
            computed_recurrence_score = round((dist_score * 0.6) + (type_similarity * 0.4), 4)

            # Check related maintenance job and verification
            link_stmt = select(MaintenanceDamageLink).where(
                MaintenanceDamageLink.damage_record_id == hist.id
            )
            link = (await db.execute(link_stmt)).scalar_one_or_none()
            rel_job_id = link.maintenance_job_id if link else None

            rel_verification_id = None
            if rel_job_id:
                ver_stmt = (
                    select(RepairVerification)
                    .where(
                        RepairVerification.maintenance_job_id == rel_job_id,
                        RepairVerification.verification_status == "VERIFIED",
                    )
                    .order_by(desc(RepairVerification.created_at))
                )
                ver = (await db.execute(ver_stmt)).scalars().first()
                if ver:
                    rel_verification_id = ver.id

            rec_record = RecurrenceRecord(
                id=uuid.uuid4(),
                organization_id=organization_id,
                historical_damage_id=hist.id,
                new_damage_id=new_dmg.id,
                related_maintenance_job_id=rel_job_id,
                related_repair_verification_id=rel_verification_id,
                road_segment_id=new_dmg.road_segment_id,
                spatial_distance_meters=round(dist, 2),
                temporal_distance_days=temporal_days,
                similarity_score=type_similarity,
                recurrence_score=computed_recurrence_score,
                detection_method_version="recurrence-spatial-temporal-v1",
                status="POTENTIAL",
                evaluated_at=now,
                created_at=now,
                updated_at=now,
            )
            db.add(rec_record)
            created_records.append(rec_record)

    if created_records:
        await db.commit()
        for rec in created_records:
            await db.refresh(rec)

    return created_records


async def batch_evaluate_segment_recurrences(
    db: AsyncSession,
    road_segment_id: uuid.UUID,
    organization_id: uuid.UUID,
    max_distance_meters: float = 30.0,
) -> list[RecurrenceRecord]:
    """Evaluates all damage records on a given segment for potential recurrences."""
    damages_query = (
        select(DamageRecord)
        .where(
            DamageRecord.organization_id == organization_id,
            DamageRecord.road_segment_id == road_segment_id,
        )
        .order_by(DamageRecord.created_at.asc())
    )
    damages = list((await db.execute(damages_query)).scalars().all())

    all_created: list[RecurrenceRecord] = []
    # For each damage, check against earlier damages
    for dmg in damages:
        created = await run_recurrence_detection_for_damage(
            db, dmg.id, organization_id, max_distance_meters=max_distance_meters
        )
        all_created.extend(created)

    return all_created


async def list_recurrences(
    db: AsyncSession,
    organization_id: uuid.UUID,
    road_segment_id: uuid.UUID | None = None,
    status_filter: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[RecurrenceRecordResponse], int]:
    query = select(RecurrenceRecord).where(RecurrenceRecord.organization_id == organization_id)

    if road_segment_id:
        query = query.where(RecurrenceRecord.road_segment_id == road_segment_id)
    if status_filter:
        query = query.where(RecurrenceRecord.status == status_filter)

    query = query.options(
        selectinload(RecurrenceRecord.historical_damage).selectinload(DamageRecord.damage_type),
        selectinload(RecurrenceRecord.new_damage).selectinload(DamageRecord.damage_type),
        selectinload(RecurrenceRecord.road_segment),
    ).order_by(desc(RecurrenceRecord.recurrence_score), desc(RecurrenceRecord.created_at))

    # Execute
    results = list((await db.execute(query)).scalars().all())
    total_count = len(results)

    offset = (page - 1) * page_size
    paged_results = results[offset : offset + page_size]

    responses: list[RecurrenceRecordResponse] = []
    for r in paged_results:
        hist_coords = get_coords_from_geom(r.historical_damage.location) if r.historical_damage else None
        new_coords = get_coords_from_geom(r.new_damage.location) if r.new_damage else None

        hist_summary = (
            DamageSummaryItem(
                id=r.historical_damage.id,
                damage_type=r.historical_damage.damage_type.code if r.historical_damage.damage_type else "UNKNOWN",
                severity=r.historical_damage.severity,
                status=r.historical_damage.status,
                latitude=hist_coords[0] if hist_coords else None,
                longitude=hist_coords[1] if hist_coords else None,
                detected_at=r.historical_damage.detected_at,
            )
            if r.historical_damage
            else None
        )

        new_summary = (
            DamageSummaryItem(
                id=r.new_damage.id,
                damage_type=r.new_damage.damage_type.code if r.new_damage.damage_type else "UNKNOWN",
                severity=r.new_damage.severity,
                status=r.new_damage.status,
                latitude=new_coords[0] if new_coords else None,
                longitude=new_coords[1] if new_coords else None,
                detected_at=r.new_damage.detected_at,
            )
            if r.new_damage
            else None
        )

        responses.append(
            RecurrenceRecordResponse(
                id=r.id,
                organization_id=r.organization_id,
                historical_damage_id=r.historical_damage_id,
                new_damage_id=r.new_damage_id,
                related_maintenance_job_id=r.related_maintenance_job_id,
                related_repair_verification_id=r.related_repair_verification_id,
                road_segment_id=r.road_segment_id,
                spatial_distance_meters=float(r.spatial_distance_meters) if r.spatial_distance_meters is not None else None,
                temporal_distance_days=r.temporal_distance_days,
                similarity_score=float(r.similarity_score) if r.similarity_score is not None else None,
                recurrence_score=float(r.recurrence_score) if r.recurrence_score is not None else None,
                detection_method_version=r.detection_method_version,
                status=r.status,
                evaluated_at=r.evaluated_at,
                reviewed_by_user_id=r.reviewed_by_user_id,
                reviewed_at=r.reviewed_at,
                review_notes=r.review_notes,
                created_at=r.created_at,
                updated_at=r.updated_at,
                historical_damage=hist_summary,
                new_damage=new_summary,
                segment_name=r.road_segment.name if r.road_segment else None,
            )
        )

    return responses, total_count


async def get_recurrence_record(
    db: AsyncSession,
    recurrence_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> RecurrenceRecordResponse:
    query = (
        select(RecurrenceRecord)
        .where(
            RecurrenceRecord.id == recurrence_id,
            RecurrenceRecord.organization_id == organization_id,
        )
        .options(
            selectinload(RecurrenceRecord.historical_damage).selectinload(DamageRecord.damage_type),
            selectinload(RecurrenceRecord.new_damage).selectinload(DamageRecord.damage_type),
            selectinload(RecurrenceRecord.road_segment),
        )
    )
    r = (await db.execute(query)).scalar_one_or_none()
    if not r:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RECURRENCE_NOT_FOUND", "message": "Recurrence record not found."},
        )

    hist_coords = get_coords_from_geom(r.historical_damage.location) if r.historical_damage else None
    new_coords = get_coords_from_geom(r.new_damage.location) if r.new_damage else None

    hist_summary = (
        DamageSummaryItem(
            id=r.historical_damage.id,
            damage_type=r.historical_damage.damage_type.code if r.historical_damage.damage_type else "UNKNOWN",
            severity=r.historical_damage.severity,
            status=r.historical_damage.status,
            latitude=hist_coords[0] if hist_coords else None,
            longitude=hist_coords[1] if hist_coords else None,
            detected_at=r.historical_damage.detected_at,
        )
        if r.historical_damage
        else None
    )

    new_summary = (
        DamageSummaryItem(
            id=r.new_damage.id,
            damage_type=r.new_damage.damage_type.code if r.new_damage.damage_type else "UNKNOWN",
            severity=r.new_damage.severity,
            status=r.new_damage.status,
            latitude=new_coords[0] if new_coords else None,
            longitude=new_coords[1] if new_coords else None,
            detected_at=r.new_damage.detected_at,
        )
        if r.new_damage
        else None
    )

    return RecurrenceRecordResponse(
        id=r.id,
        organization_id=r.organization_id,
        historical_damage_id=r.historical_damage_id,
        new_damage_id=r.new_damage_id,
        related_maintenance_job_id=r.related_maintenance_job_id,
        related_repair_verification_id=r.related_repair_verification_id,
        road_segment_id=r.road_segment_id,
        spatial_distance_meters=float(r.spatial_distance_meters) if r.spatial_distance_meters is not None else None,
        temporal_distance_days=r.temporal_distance_days,
        similarity_score=float(r.similarity_score) if r.similarity_score is not None else None,
        recurrence_score=float(r.recurrence_score) if r.recurrence_score is not None else None,
        detection_method_version=r.detection_method_version,
        status=r.status,
        evaluated_at=r.evaluated_at,
        reviewed_by_user_id=r.reviewed_by_user_id,
        reviewed_at=r.reviewed_at,
        review_notes=r.review_notes,
        created_at=r.created_at,
        updated_at=r.updated_at,
        historical_damage=hist_summary,
        new_damage=new_summary,
        segment_name=r.road_segment.name if r.road_segment else None,
    )


async def review_recurrence_record(
    db: AsyncSession,
    recurrence_id: uuid.UUID,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    new_status: str,
    notes: str | None = None,
) -> RecurrenceRecordResponse:
    query = select(RecurrenceRecord).where(
        RecurrenceRecord.id == recurrence_id,
        RecurrenceRecord.organization_id == organization_id,
    )
    rec = (await db.execute(query)).scalar_one_or_none()
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RECURRENCE_NOT_FOUND", "message": "Recurrence record not found."},
        )

    now = utc_now()
    rec.status = new_status
    rec.reviewed_by_user_id = user_id
    rec.reviewed_at = now
    rec.review_notes = notes
    rec.updated_at = now

    await db.commit()
    return await get_recurrence_record(db, recurrence_id, organization_id)


async def get_segment_historical_timeline(
    db: AsyncSession,
    road_segment_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> SegmentHistoricalTimelineResponse:
    """Builds a complete, un-overwritten chronological lifecycle timeline for a road segment.
    
    Shows:
    Damage Detected -> Maintenance Created -> Maintenance Completed -> Repair Verified -> Recurrence Detected
    """
    segment = await db.get(RoadSegment, road_segment_id)
    if not segment or segment.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SEGMENT_NOT_FOUND", "message": "Road segment not found."},
        )

    events: list[SegmentTimelineEvent] = []

    # 1. Damage Records
    damages_query = (
        select(DamageRecord)
        .where(
            DamageRecord.organization_id == organization_id,
            DamageRecord.road_segment_id == road_segment_id,
        )
        .options(selectinload(DamageRecord.damage_type))
    )
    damages = list((await db.execute(damages_query)).scalars().all())

    for dmg in damages:
        dmg_type_name = dmg.damage_type.name if dmg.damage_type else "Road Defect"
        events.append(
            SegmentTimelineEvent(
                event_type="DAMAGE_DETECTED",
                timestamp=dmg.detected_at or dmg.created_at,
                entity_id=dmg.id,
                title=f"{dmg_type_name} Detected",
                description=dmg.notes or f"Damage registered with {dmg.severity} severity.",
                severity=dmg.severity,
                status=dmg.status,
                metadata={
                    "damage_type": dmg.damage_type.code if dmg.damage_type else "UNKNOWN",
                    "severity_score": float(dmg.severity_score) if dmg.severity_score else None,
                    "confidence": float(dmg.confidence) if dmg.confidence else None,
                },
            )
        )

    # 2. Maintenance Jobs
    jobs_query = (
        select(MaintenanceJob)
        .where(
            MaintenanceJob.organization_id == organization_id,
            MaintenanceJob.road_segment_id == road_segment_id,
        )
    )
    jobs = list((await db.execute(jobs_query)).scalars().all())

    for job in jobs:
        events.append(
            SegmentTimelineEvent(
                event_type="MAINTENANCE_CREATED",
                timestamp=job.created_at,
                entity_id=job.id,
                title=f"Maintenance Created: {job.title}",
                description=job.description,
                severity=job.priority_level,
                status=job.status,
                metadata={"priority_score": float(job.priority_score) if job.priority_score else None},
            )
        )
        if job.completed_at:
            events.append(
                SegmentTimelineEvent(
                    event_type="MAINTENANCE_COMPLETED",
                    timestamp=job.completed_at,
                    entity_id=job.id,
                    title=f"Maintenance Completed: {job.title}",
                    description=job.completion_notes or "Work order completed on site.",
                    severity=job.priority_level,
                    status=job.status,
                    metadata={},
                )
            )

    # 3. Repair Verifications
    ver_query = (
        select(RepairVerification)
        .join(MaintenanceJob, MaintenanceJob.id == RepairVerification.maintenance_job_id)
        .where(
            RepairVerification.organization_id == organization_id,
            MaintenanceJob.road_segment_id == road_segment_id,
        )
    )
    verifications = list((await db.execute(ver_query)).scalars().all())

    for ver in verifications:
        events.append(
            SegmentTimelineEvent(
                event_type="REPAIR_VERIFIED",
                timestamp=ver.verified_at or ver.created_at,
                entity_id=ver.id,
                title=f"Repair Verification: {ver.verification_status}",
                description=ver.reviewer_notes or "Authorized repair sign-off.",
                status=ver.verification_status,
                metadata={
                    "ai_confidence": float(ver.ai_confidence) if ver.ai_confidence else None,
                    "findings": ver.findings,
                },
            )
        )

    # 4. Recurrence Records
    rec_query = (
        select(RecurrenceRecord)
        .where(
            RecurrenceRecord.organization_id == organization_id,
            RecurrenceRecord.road_segment_id == road_segment_id,
        )
    )
    recurrences = list((await db.execute(rec_query)).scalars().all())

    for rec in recurrences:
        events.append(
            SegmentTimelineEvent(
                event_type="RECURRENCE_DETECTED",
                timestamp=rec.evaluated_at or rec.created_at,
                entity_id=rec.id,
                title=f"Recurrence Detected ({rec.status})",
                description=rec.review_notes or f"Damage recurring after {rec.temporal_distance_days} days at ~{rec.spatial_distance_meters}m distance.",
                status=rec.status,
                metadata={
                    "recurrence_score": float(rec.recurrence_score) if rec.recurrence_score else None,
                    "spatial_distance_meters": float(rec.spatial_distance_meters) if rec.spatial_distance_meters else None,
                    "temporal_distance_days": rec.temporal_distance_days,
                },
            )
        )

    # Sort chronological ascending
    events.sort(key=lambda e: ensure_utc(e.timestamp))

    return SegmentHistoricalTimelineResponse(
        road_segment_id=segment.id,
        road_name=segment.name,
        segment_number=segment.segment_number,
        total_events=len(events),
        events=events,
    )
