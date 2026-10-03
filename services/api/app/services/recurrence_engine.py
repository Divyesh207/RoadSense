"""
Deterministic recurrence detection and escalation (Phase 3C).

A recurrence is damage that reappears where earlier damage was repaired. When a damage
record becomes CONFIRMED it is compared with earlier damage that:
  - belongs to the same organization (and the same segment when the new damage has one),
  - lies within the grouping radius (PostGIS ST_DWithin on geography; haversine on SQLite),
  - has the same damage type (automatic mode),
  - was actually repaired: status REPAIRED, or its maintenance job reached COMPLETED.
Matches become RecurrenceRecords (status POTENTIAL until a person reviews them) that keep
the original damage, its repair job and that job's final verification untouched.

Escalation is rule-based (no prediction): repeated recurrence at the location, a repair
whose verification was not SUCCESSFUL, recurrence soon after repair, or high/critical
severity. Every rule that fired is stored with its inputs and audited.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from geoalchemy2 import Geography
from sqlalchemy import cast, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.damage import DamageRecord
from app.models.history import RecurrenceRecord
from app.models.maintenance import MaintenanceDamageLink, MaintenanceJob
from app.models.repair import RepairVerification
from app.services.audit_service import AuditService
from app.services.spatial import haversine_distance_m, wkt_or_geom_to_point
from app.services.spatial_queries import is_postgres

RULES_VERSION = "recurrence-rules-v1.0.0"
REPAIRED_JOB_STATES = ("COMPLETED", "VERIFICATION_PENDING", "VERIFIED", "REJECTED")
INACTIVE_STATUSES = ("DISMISSED", "FALSE_POSITIVE")
EARLY_RECURRENCE_DAYS = 90
LEVELS = ("NONE", "ELEVATED", "CRITICAL")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


async def _candidates(
    db: AsyncSession, org_id: uuid.UUID, new: DamageRecord, lat: float, lon: float, radius: float
) -> list[tuple[DamageRecord, float]]:
    new_time = _utc(new.detected_at or new.created_at) or utc_now()
    filters = [
        DamageRecord.organization_id == org_id,
        DamageRecord.id != new.id,
        DamageRecord.location.is_not(None),
        DamageRecord.created_at <= new_time,
    ]
    if new.road_segment_id:
        filters.append(DamageRecord.road_segment_id == new.road_segment_id)
    if is_postgres(db):
        target = cast(func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326), Geography)
        geog = cast(DamageRecord.location, Geography)
        dist = func.ST_Distance(geog, target)
        rows = (
            await db.execute(
                select(DamageRecord, dist.label("d")).where(*filters, func.ST_DWithin(geog, target, radius)).order_by(dist)
            )
        ).all()
        return [(r[0], float(r[1])) for r in rows]
    out = []
    for rec in (await db.execute(select(DamageRecord).where(*filters))).scalars():
        pt = wkt_or_geom_to_point(rec.location)
        if pt is None:
            continue
        d = haversine_distance_m(lat, lon, pt[0], pt[1])
        if d <= radius:
            out.append((rec, d))
    return sorted(out, key=lambda x: x[1])


async def final_verification(db: AsyncSession, job_id: uuid.UUID) -> tuple[RepairVerification | None, str | None, str]:
    """(verification, result, source) for a job: the latest human decision, else the latest
    completed automated analysis, else none."""
    human = (
        await db.execute(
            select(RepairVerification)
            .where(
                RepairVerification.maintenance_job_id == job_id,
                or_(
                    RepairVerification.verification_type.in_(("HUMAN_REVIEW", "HUMAN_SIGNOFF")),
                    RepairVerification.verified_by_user_id.is_not(None),
                ),
            )
            .order_by(desc(RepairVerification.created_at))
            .limit(1)
        )
    ).scalar_one_or_none()
    if human is not None:
        result = human.result or {"VERIFIED": "SUCCESSFUL", "REJECTED": "SUBSTANDARD"}.get(human.verification_status)
        return human, result, "HUMAN"
    auto = (
        await db.execute(
            select(RepairVerification)
            .where(
                RepairVerification.maintenance_job_id == job_id,
                RepairVerification.verification_type == "AUTOMATED_IMAGE_ANALYSIS",
                RepairVerification.verification_status == "COMPLETED",
            )
            .order_by(desc(RepairVerification.created_at))
            .limit(1)
        )
    ).scalar_one_or_none()
    if auto is not None:
        return auto, auto.result, "AUTOMATED"
    return None, None, "NONE"


async def _repair_context(db: AsyncSession, hist: DamageRecord) -> dict[str, Any] | None:
    jobs = (
        await db.execute(
            select(MaintenanceJob)
            .join(MaintenanceDamageLink, MaintenanceDamageLink.maintenance_job_id == MaintenanceJob.id)
            .where(MaintenanceDamageLink.damage_record_id == hist.id)
            .order_by(desc(MaintenanceJob.completed_at), desc(MaintenanceJob.created_at))
        )
    ).scalars().all()
    job = next((j for j in jobs if j.completed_at is not None or j.status in REPAIRED_JOB_STATES), None)
    if job is None and hist.status != "REPAIRED":
        return None  # never repaired: the same damage, not a recurrence
    ctx: dict[str, Any] = {"job": job, "verification": None, "result": None, "result_source": "NONE"}
    if job is not None:
        ctx["verification"], ctx["result"], ctx["result_source"] = await final_verification(db, job.id)
        ctx["repaired_at"] = _utc(job.verified_at or job.completed_at)
    else:
        ctx["repaired_at"] = _utc(hist.updated_at)
    return ctx


def escalation(factors: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    reasons: list[dict[str, Any]] = []
    n = factors["recurrence_number_at_location"]
    if n >= 3:
        reasons.append({"code": "REPEATED_RECURRENCE", "level": "CRITICAL", "detail": f"Recurrence #{n} at this location."})
    elif n == 2:
        reasons.append({"code": "REPEATED_RECURRENCE", "level": "ELEVATED", "detail": "Second recurrence at this location."})
    result = factors["previous_verification_result"]
    if result == "SUBSTANDARD":
        reasons.append({"code": "SUBSTANDARD_REPAIR", "level": "ELEVATED",
                        "detail": "The previous repair was assessed SUBSTANDARD."})
    elif result in (None, "UNRESOLVED"):
        reasons.append({"code": "UNVERIFIED_REPAIR", "level": "ELEVATED",
                        "detail": "The previous repair was never verified as SUCCESSFUL "
                                  f"({'no verification' if result is None else 'UNRESOLVED'})."})
    days = factors["days_since_repair"]
    if days is not None and days <= EARLY_RECURRENCE_DAYS:
        reasons.append({"code": "EARLY_RECURRENCE", "level": "ELEVATED",
                        "detail": f"Damage reappeared {days} day(s) after repair (<= {EARLY_RECURRENCE_DAYS})."})
    sev = str(factors["new_damage_severity"]).upper()
    if sev == "CRITICAL":
        reasons.append({"code": "CRITICAL_SEVERITY", "level": "CRITICAL", "detail": "Recurring damage is CRITICAL."})
    elif sev == "HIGH":
        reasons.append({"code": "HIGH_SEVERITY", "level": "ELEVATED", "detail": "Recurring damage is HIGH severity."})
    level = max((r["level"] for r in reasons), key=LEVELS.index, default="NONE")
    return level, reasons


async def evaluate_recurrence(
    db: AsyncSession,
    org_id: uuid.UUID,
    new: DamageRecord,
    radius_m: float | None = None,
    require_same_type: bool = True,
    actor_user_id: uuid.UUID | None = None,
    request_id: str | None = None,
) -> list[RecurrenceRecord]:
    """Create RecurrenceRecords for `new` (idempotent per historical/new pair). Does not commit."""
    pt = wkt_or_geom_to_point(new.location) if new.location is not None else None
    if pt is None:
        return []
    radius = settings.DAMAGE_GROUPING_RADIUS_METERS if radius_m is None else radius_m
    now = utc_now()
    new_time = _utc(new.detected_at or new.created_at) or now
    created: list[RecurrenceRecord] = []
    for hist, dist in await _candidates(db, org_id, new, pt[0], pt[1], radius):
        same_type = hist.damage_type_id == new.damage_type_id
        if require_same_type and not same_type:
            continue
        exists = (
            await db.execute(
                select(RecurrenceRecord.id).where(
                    RecurrenceRecord.historical_damage_id == hist.id, RecurrenceRecord.new_damage_id == new.id
                )
            )
        ).first()
        if exists:
            continue
        repair = await _repair_context(db, hist)
        if repair is None:
            continue
        prior = (
            await db.execute(
                select(func.count(RecurrenceRecord.id)).where(
                    or_(RecurrenceRecord.historical_damage_id == hist.id, RecurrenceRecord.new_damage_id == hist.id),
                    RecurrenceRecord.status.not_in(INACTIVE_STATUSES),
                )
            )
        ).scalar() or 0
        repaired_at = repair["repaired_at"]
        days_since = (new_time - repaired_at).days if repaired_at else None
        type_similarity = 1.0 if same_type else 0.5
        proximity = max(0.0, 1.0 - dist / radius) if radius > 0 else 0.0
        job = repair["job"]
        ver = repair["verification"]
        factors = {
            "rules_version": RULES_VERSION,
            "distance_meters": round(dist, 3),
            "radius_meters": radius,
            "same_damage_type": same_type,
            "historical_status": hist.status,
            "repair_job_id": str(job.id) if job else None,
            "repair_job_status": job.status if job else None,
            "repaired_at": repaired_at.isoformat() if repaired_at else None,
            "days_since_repair": days_since,
            "previous_verification_id": str(ver.id) if ver else None,
            "previous_verification_result": repair["result"],
            "previous_verification_source": repair["result_source"],
            "new_damage_severity": new.severity,
            "new_damage_observation_count": new.observation_count or 1,
            "recurrence_number_at_location": prior + 1,
            "recurrence_score_definition": "0.6 * (1 - distance / radius) + 0.4 * type_match; descriptive, not a probability",
        }
        level, reasons = escalation(factors)
        rec = RecurrenceRecord(
            id=uuid.uuid4(),
            organization_id=org_id,
            historical_damage_id=hist.id,
            new_damage_id=new.id,
            related_maintenance_job_id=job.id if job else None,
            related_repair_verification_id=ver.id if ver else None,
            road_segment_id=new.road_segment_id,
            spatial_distance_meters=round(dist, 2),
            temporal_distance_days=max(0, (new_time - (_utc(hist.detected_at or hist.created_at) or new_time)).days),
            similarity_score=type_similarity,
            recurrence_score=round(proximity * 0.6 + type_similarity * 0.4, 4),
            detection_method_version=RULES_VERSION,
            status="POTENTIAL",
            rule_factors=factors,
            escalation_level=level,
            escalation_reasons=reasons,
            escalated_at=now if level != "NONE" else None,
            evaluated_at=now,
            created_at=now,
            updated_at=now,
        )
        db.add(rec)
        created.append(rec)
        await db.flush()
        if level != "NONE":
            await AuditService.record_audit_event(
                db, action="RECURRENCE_ESCALATED", entity_type="recurrence_record", entity_id=rec.id,
                actor_user_id=actor_user_id, organization_id=org_id, request_id=request_id,
                after_data={"escalation_level": level, "reasons": reasons},
                metadata={"historical_damage_id": str(hist.id), "new_damage_id": str(new.id),
                          "rules_version": RULES_VERSION},
            )
    return created


async def on_damage_confirmed(
    db: AsyncSession, org_id: uuid.UUID, damage: DamageRecord, actor_user_id: uuid.UUID | None = None,
    request_id: str | None = None,
) -> list[RecurrenceRecord]:
    """Automatic recurrence check when damage is confirmed. Commits when records were created."""
    created = await evaluate_recurrence(db, org_id, damage, actor_user_id=actor_user_id, request_id=request_id)
    if created:
        await db.commit()
    return created


async def on_damage_rejected(
    db: AsyncSession, org_id: uuid.UUID, damage: DamageRecord, actor_user_id: uuid.UUID | None = None,
    request_id: str | None = None,
) -> int:
    """A rejected damage cannot be a recurrence: its open POTENTIAL records are dismissed (kept, not deleted)."""
    recs = (
        await db.execute(
            select(RecurrenceRecord).where(
                RecurrenceRecord.organization_id == org_id,
                RecurrenceRecord.new_damage_id == damage.id,
                RecurrenceRecord.status == "POTENTIAL",
            )
        )
    ).scalars().all()
    now = utc_now()
    for rec in recs:
        rec.status = "DISMISSED"
        rec.reviewed_by_user_id = actor_user_id
        rec.reviewed_at = now
        rec.review_notes = "Dismissed automatically: the new damage was rejected at review."
        rec.updated_at = now
        await AuditService.record_audit_event(
            db, action="RECURRENCE_DISMISSED", entity_type="recurrence_record", entity_id=rec.id,
            actor_user_id=actor_user_id, organization_id=org_id, request_id=request_id,
            before_data={"status": "POTENTIAL"}, after_data={"status": "DISMISSED"},
            metadata={"reason": "NEW_DAMAGE_REJECTED"},
        )
    if recs:
        await db.commit()
    return len(recs)
