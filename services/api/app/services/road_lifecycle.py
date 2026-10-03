"""
Keeps derived road intelligence current when damage state changes.

After damage is created, grouped, reviewed, re-classified, scheduled or repaired:
  1. the affected segments' and roads' RoadHealthSnapshots are recalculated and
     persisted (skipped when nothing changed, so no duplicate snapshots), then
  2. open AUTO-priority maintenance jobs linked to that damage, or on those
     segments, are re-prioritised.

Called by services after their own commit. A failure here is logged and rolled back
but does not undo the damage change that triggered it.
"""

import logging
import uuid
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.damage import DamageRecord
from app.models.maintenance import MaintenanceDamageLink, MaintenanceJob
from app.models.road import Road, RoadSegment
from app.services.health_engine import calculate_road_health, calculate_segment_health
from app.services.priority_engine import CLOSED_JOB_STATUSES, recalculate_job_priority

logger = logging.getLogger(__name__)


async def refresh_after_damage_change(
    db: AsyncSession, organization_id: uuid.UUID, damages: Iterable[DamageRecord]
) -> None:
    damages = list(damages)
    damage_ids = {d.id for d in damages}
    segment_ids = {d.road_segment_id for d in damages if d.road_segment_id}
    road_ids = {d.road_id for d in damages if d.road_id}
    if not damage_ids:
        return
    try:
        for seg_id in segment_ids:
            segment = await db.get(RoadSegment, seg_id)
            if segment is not None and segment.organization_id == organization_id:
                road_ids.add(segment.road_id)
                await calculate_segment_health(db, organization_id, segment, persist=True, dedupe=True)
        for road_id in road_ids:
            road = await db.get(Road, road_id)
            if road is not None and road.organization_id == organization_id:
                await calculate_road_health(db, organization_id, road, persist=True, dedupe=True)

        job_filters = [MaintenanceDamageLink.damage_record_id.in_(damage_ids)]
        linked_job_ids = set(
            (
                await db.execute(
                    select(MaintenanceDamageLink.maintenance_job_id).where(*job_filters)
                )
            ).scalars()
        )
        stmt = select(MaintenanceJob).where(
            MaintenanceJob.organization_id == organization_id,
            MaintenanceJob.status.not_in(CLOSED_JOB_STATUSES),
        )
        if segment_ids:
            stmt = stmt.where(
                MaintenanceJob.id.in_(linked_job_ids) | MaintenanceJob.road_segment_id.in_(segment_ids)
            )
        else:
            stmt = stmt.where(MaintenanceJob.id.in_(linked_job_ids))
        changed = False
        for job in (await db.execute(stmt)).scalars().all():
            changed |= await recalculate_job_priority(db, job)
        if changed:
            await db.commit()
    except SQLAlchemyError:
        logger.exception("Road health/priority refresh failed for damage %s", sorted(map(str, damage_ids)))
        await db.rollback()


async def refresh_road_health(db: AsyncSession, organization_id: uuid.UUID, road: Road) -> None:
    """Recalculate all active segments of a road and the road itself (e.g. after its traffic changed),
    then re-prioritise open AUTO jobs on that road."""
    try:
        segments = (
            await db.execute(
                select(RoadSegment).where(
                    RoadSegment.road_id == road.id,
                    RoadSegment.organization_id == organization_id,
                    RoadSegment.is_active.is_(True),
                )
            )
        ).scalars().all()
        for segment in segments:
            await calculate_segment_health(db, organization_id, segment, persist=True, dedupe=True)
        await calculate_road_health(db, organization_id, road, persist=True, dedupe=True)
        jobs = (
            await db.execute(
                select(MaintenanceJob).where(
                    MaintenanceJob.organization_id == organization_id,
                    MaintenanceJob.road_id == road.id,
                    MaintenanceJob.status.not_in(CLOSED_JOB_STATUSES),
                )
            )
        ).scalars().all()
        changed = False
        for job in jobs:
            changed |= await recalculate_job_priority(db, job)
        if changed:
            await db.commit()
    except SQLAlchemyError:
        logger.exception("Road health refresh failed for road %s", road.id)
        await db.rollback()
