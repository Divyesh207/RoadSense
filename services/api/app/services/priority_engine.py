"""
Deterministic, explainable maintenance priority (synopsis: "scoring rules based on
damage severity and historical wear").

score = severity base (unchanged bands from the original rule)
      + frequency     2 pts per repeat sighting of linked damage      (max 10)
      + recurrence    5 pts per active recurrence on the location     (max 15)
      + prior repairs 4 pts per earlier verified repair on location   (max 12)
      + road health   0.15 x (100 - latest health score), if known    (max 15)
capped at 100. The level is the band of the final score, but never lower than the
level implied by the most severe linked damage. Every input and component is
returned in `factors` so the result can be audited; unknown inputs contribute 0
and are recorded as unknown rather than estimated.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.damage import DamageRecord
from app.models.history import RecurrenceRecord
from app.models.intelligence import RoadHealthSnapshot
from app.models.maintenance import MaintenanceDamageLink, MaintenanceJob

PRIORITY_VERSION = "priority-v2.0.0"
LEVELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
INACTIVE_RECURRENCE_STATUSES = ("DISMISSED", "FALSE_POSITIVE")
CLOSED_JOB_STATUSES = ("VERIFIED", "CANCELLED")

FREQUENCY_POINTS_PER_REPEAT, FREQUENCY_CAP = 2.0, 10.0
RECURRENCE_POINTS_EACH, RECURRENCE_CAP = 5.0, 15.0
PRIOR_REPAIR_POINTS_EACH, PRIOR_REPAIR_CAP = 4.0, 12.0
HEALTH_DEFICIT_FACTOR, HEALTH_CAP = 0.15, 15.0


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def compute_priority_from_damages(damages: Sequence[DamageRecord]) -> tuple[str, float]:
    """Severity base: level from the most severe damage, score by band and count (original rule)."""
    if not damages:
        return "MEDIUM", 50.0

    severities = [str(d.severity).upper() for d in damages]
    if "CRITICAL" in severities:
        return "CRITICAL", round(min(100.0, 85.0 + (len(damages) * 2.5)), 2)
    if "HIGH" in severities:
        return "HIGH", round(min(84.0, 65.0 + (len(damages) * 3.0)), 2)
    if "MEDIUM" in severities:
        return "MEDIUM", round(min(64.0, 40.0 + (len(damages) * 3.0)), 2)
    return "LOW", round(min(39.0, 20.0 + (len(damages) * 2.0)), 2)


def band_for_score(score: float) -> str:
    if score >= 85.0:
        return "CRITICAL"
    if score >= 65.0:
        return "HIGH"
    if score >= 40.0:
        return "MEDIUM"
    return "LOW"


@dataclass
class PriorityResult:
    level: str
    score: float
    factors: dict[str, Any]


async def _latest_health(
    db: AsyncSession, organization_id: uuid.UUID, segment_ids: set[uuid.UUID], road_ids: set[uuid.UUID]
) -> tuple[float | None, str]:
    """Worst latest segment health among the location's segments; else road-level; else unknown."""
    scores: list[float] = []
    for seg_id in segment_ids:
        snap = (
            await db.execute(
                select(RoadHealthSnapshot)
                .where(RoadHealthSnapshot.organization_id == organization_id, RoadHealthSnapshot.road_segment_id == seg_id)
                .order_by(desc(RoadHealthSnapshot.calculated_at))
                .limit(1)
            )
        ).scalar_one_or_none()
        if snap is not None and snap.health_score is not None:
            scores.append(float(snap.health_score))
    if scores:
        return min(scores), "segment"
    for road_id in road_ids:
        snap = (
            await db.execute(
                select(RoadHealthSnapshot)
                .where(
                    RoadHealthSnapshot.organization_id == organization_id,
                    RoadHealthSnapshot.road_id == road_id,
                    RoadHealthSnapshot.road_segment_id.is_(None),
                )
                .order_by(desc(RoadHealthSnapshot.calculated_at))
                .limit(1)
            )
        ).scalar_one_or_none()
        if snap is not None and snap.health_score is not None:
            scores.append(float(snap.health_score))
    if scores:
        return min(scores), "road"
    return None, "unknown"


async def compute_priority(
    db: AsyncSession,
    organization_id: uuid.UUID,
    damages: Sequence[DamageRecord],
    road_id: uuid.UUID | None = None,
    segment_id: uuid.UUID | None = None,
    exclude_job_id: uuid.UUID | None = None,
) -> PriorityResult:
    base_level, base_score = compute_priority_from_damages(damages)
    damage_ids = [d.id for d in damages]
    segment_ids = {s for s in [segment_id, *[d.road_segment_id for d in damages]] if s}
    road_ids = {r for r in [road_id, *[d.road_id for d in damages]] if r}

    repeats = sum(max(0, (d.observation_count or 1) - 1) for d in damages)
    frequency_pts = min(FREQUENCY_CAP, repeats * FREQUENCY_POINTS_PER_REPEAT)

    recurrence_count = 0
    scope = []
    if damage_ids:
        scope += [RecurrenceRecord.new_damage_id.in_(damage_ids), RecurrenceRecord.historical_damage_id.in_(damage_ids)]
    if segment_ids:
        scope.append(RecurrenceRecord.road_segment_id.in_(segment_ids))
    if scope:
        recurrence_count = (
            await db.execute(
                select(func.count(func.distinct(RecurrenceRecord.id))).where(
                    RecurrenceRecord.organization_id == organization_id,
                    RecurrenceRecord.status.not_in(INACTIVE_RECURRENCE_STATUSES),
                    or_(*scope),
                )
            )
        ).scalar() or 0
    recurrence_pts = min(RECURRENCE_CAP, recurrence_count * RECURRENCE_POINTS_EACH)

    prior_repairs = 0
    location_scope = (
        MaintenanceJob.road_segment_id.in_(segment_ids) if segment_ids
        else MaintenanceJob.road_id.in_(road_ids) if road_ids else None
    )
    if location_scope is not None:
        stmt = select(func.count(MaintenanceJob.id)).where(
            MaintenanceJob.organization_id == organization_id,
            MaintenanceJob.status == "VERIFIED",
            location_scope,
        )
        if exclude_job_id is not None:
            stmt = stmt.where(MaintenanceJob.id != exclude_job_id)
        prior_repairs = (await db.execute(stmt)).scalar() or 0
    prior_repair_pts = min(PRIOR_REPAIR_CAP, prior_repairs * PRIOR_REPAIR_POINTS_EACH)

    health_score, health_scope = await _latest_health(db, organization_id, segment_ids, road_ids)
    health_pts = 0.0 if health_score is None else min(HEALTH_CAP, round((100.0 - health_score) * HEALTH_DEFICIT_FACTOR, 2))

    total = round(min(100.0, base_score + frequency_pts + recurrence_pts + prior_repair_pts + health_pts), 2)
    level = LEVELS[max(LEVELS.index(base_level), LEVELS.index(band_for_score(total)))]
    factors = {
        "method": "RULE_BASED",
        "version": PRIORITY_VERSION,
        "inputs": {
            "linked_damage_count": len(damages),
            "max_severity_level": base_level,
            "repeat_observations": repeats,
            "active_recurrences": recurrence_count,
            "prior_verified_repairs": prior_repairs,
            "road_health_score": health_score,
            "road_health_scope": health_scope,
        },
        "components": {
            "severity_base": base_score,
            "frequency": frequency_pts,
            "recurrence": recurrence_pts,
            "prior_repairs": prior_repair_pts,
            "road_health": health_pts,
        },
        "level_floor_from_severity": base_level,
        "calculated_at": utc_now().isoformat(),
    }
    return PriorityResult(level=level, score=total, factors=factors)


async def recalculate_job_priority(db: AsyncSession, job: MaintenanceJob) -> bool:
    """Recompute an AUTO-priority open job from its linked damage. Manual priorities are left alone.
    Does not commit; returns True if the job was updated."""
    mode = (job.priority_factors or {}).get("mode")
    if mode != "AUTO" or job.status in CLOSED_JOB_STATUSES:
        return False
    damages = list(
        (
            await db.execute(
                select(DamageRecord)
                .join(MaintenanceDamageLink, MaintenanceDamageLink.damage_record_id == DamageRecord.id)
                .where(MaintenanceDamageLink.maintenance_job_id == job.id, DamageRecord.status != "REJECTED")
            )
        ).scalars().all()
    )
    if not damages:
        return False
    result = await compute_priority(db, job.organization_id, damages, job.road_id, job.road_segment_id, job.id)
    previous = job.priority_factors or {}
    if (
        job.priority_level == result.level
        and job.priority_score is not None
        and float(job.priority_score) == result.score
        and previous.get("inputs") == result.factors["inputs"]
        and previous.get("components") == result.factors["components"]
    ):
        return False
    job.priority_level = result.level
    job.priority_score = result.score
    job.priority_factors = {**result.factors, "mode": "AUTO"}
    job.updated_at = utc_now()
    return True
