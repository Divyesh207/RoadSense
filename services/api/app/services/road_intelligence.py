"""
Historical road intelligence read models (Phase 3C).

Aggregates stored records only: no values are estimated or filled in. Missing data is
returned as null/empty so the UI can show an honest no-data state.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.damage import DamageRecord, DamageReview
from app.models.history import RecurrenceRecord
from app.models.identity import Organization, User
from app.models.inspection import Inspection
from app.models.intelligence import RoadHealthSnapshot
from app.models.maintenance import (
    MaintenanceDamageLink,
    MaintenanceJob,
    MaintenanceStatusHistory,
)
from app.models.repair import RepairEvidence, RepairVerification
from app.models.road import Road, RoadSegment
from app.services.recurrence_engine import final_verification
from app.services.spatial import wkt_or_geom_to_point

ACTIVE_DAMAGE = ("DETECTED", "CONFIRMED", "MAINTENANCE_SCHEDULED", "IN_PROGRESS")
ACTIVE_RECURRENCE = ("POTENTIAL", "CONFIRMED")


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return (dt if dt.tzinfo else dt.replace(tzinfo=UTC)).isoformat()


def _snapshot(s: RoadHealthSnapshot) -> dict[str, Any]:
    f = s.factors or {}
    return {
        "id": str(s.id),
        "road_segment_id": str(s.road_segment_id) if s.road_segment_id else None,
        "health_score": float(s.health_score) if s.health_score is not None else None,
        "health_status": s.health_status,
        "calculation_version": s.calculation_version,
        "calculated_at": _iso(s.calculated_at),
        "score_deductions": f.get("score_deductions") or {},
        "recurrence_count": f.get("recurrence_count"),
        "total_damages": f.get("total_damages"),
        "traffic": f.get("traffic"),
    }


async def contractor_history(db: AsyncSession, org_id: uuid.UUID) -> list[dict[str, Any]]:
    """Per assignee (user or contractor organization) record of assigned jobs and outcomes."""
    jobs = (
        await db.execute(
            select(MaintenanceJob).where(
                MaintenanceJob.organization_id == org_id,
                or_(MaintenanceJob.assigned_to_user_id.is_not(None), MaintenanceJob.assigned_to_organization_id.is_not(None)),
            )
        )
    ).scalars().all()
    groups: dict[tuple[str, uuid.UUID], list[MaintenanceJob]] = {}
    for job in jobs:
        if job.assigned_to_organization_id:
            groups.setdefault(("CONTRACTOR", job.assigned_to_organization_id), []).append(job)
        if job.assigned_to_user_id:
            groups.setdefault(("USER", job.assigned_to_user_id), []).append(job)
    out = []
    for (kind, aid), items in groups.items():
        entity = await db.get(Organization if kind == "CONTRACTOR" else User, aid)
        outcomes: dict[str, int] = {}
        for job in items:
            _, result, _ = await final_verification(db, job.id)
            if result:
                outcomes[result] = outcomes.get(result, 0) + 1
        job_ids = [j.id for j in items]
        recurrences = (
            await db.execute(
                select(func.count(RecurrenceRecord.id)).where(
                    RecurrenceRecord.related_maintenance_job_id.in_(job_ids),
                    RecurrenceRecord.status.in_(ACTIVE_RECURRENCE),
                )
            )
        ).scalar() or 0
        out.append({
            "assignee_type": kind,
            "assignee_id": str(aid),
            "name": (entity.name if kind == "CONTRACTOR" else entity.full_name) if entity else None,
            "assigned_jobs": len(items),
            "completed_jobs": sum(1 for j in items if j.completed_at is not None),
            "verified_jobs": sum(1 for j in items if j.status == "VERIFIED"),
            "rejected_jobs": sum(1 for j in items if j.status == "REJECTED"),
            "open_jobs": sum(1 for j in items if j.status not in ("VERIFIED", "CANCELLED")),
            "verification_outcomes": outcomes,
            "recurrences_after_repair": recurrences,
            "jobs": [
                {"id": str(j.id), "title": j.title, "status": j.status, "completed_at": _iso(j.completed_at)}
                for j in sorted(items, key=lambda j: j.created_at, reverse=True)
            ],
        })
    return sorted(out, key=lambda x: (-x["assigned_jobs"], x["name"] or ""))


async def verification_overview(db: AsyncSession, org_id: uuid.UUID, limit: int = 100) -> list[dict[str, Any]]:
    autos = (
        await db.execute(
            select(RepairVerification)
            .where(
                RepairVerification.organization_id == org_id,
                RepairVerification.verification_type == "AUTOMATED_IMAGE_ANALYSIS",
            )
            .order_by(desc(RepairVerification.created_at))
            .limit(limit)
        )
    ).scalars().all()
    out = []
    for a in autos:
        job = await db.get(MaintenanceJob, a.maintenance_job_id)
        review = (
            await db.execute(
                select(RepairVerification)
                .where(RepairVerification.reviewed_verification_id == a.id)
                .order_by(desc(RepairVerification.created_at))
                .limit(1)
            )
        ).scalar_one_or_none()
        f = a.findings or {}
        out.append({
            "verification_id": str(a.id),
            "maintenance_job_id": str(a.maintenance_job_id),
            "job_title": job.title if job else None,
            "job_status": job.status if job else None,
            "status": a.verification_status,
            "automated_result": a.result,
            "reason_code": f.get("reason_code"),
            "before_detection_count": f.get("before_detection_count"),
            "after_detection_count": f.get("after_detection_count"),
            "residual_detection_count": f.get("residual_detection_count"),
            "model_name": a.model_name,
            "model_version": a.model_version,
            "algorithm_version": a.algorithm_version,
            "analysed_at": _iso(a.updated_at if a.verification_status == "COMPLETED" else None),
            "requested_at": _iso(a.created_at),
            "review_decision": review.review_decision if review else None,
            "final_result": review.result if review else None,
            "reviewed_at": _iso(review.verified_at) if review else None,
            "reviewer_user_id": str(review.verified_by_user_id) if review and review.verified_by_user_id else None,
            "reviewer_notes": review.reviewer_notes if review else None,
        })
    return out


async def recurrence_overview(db: AsyncSession, org_id: uuid.UUID, limit: int = 200) -> list[dict[str, Any]]:
    recs = (
        await db.execute(
            select(RecurrenceRecord)
            .where(RecurrenceRecord.organization_id == org_id)
            .options(
                selectinload(RecurrenceRecord.new_damage).selectinload(DamageRecord.damage_type),
                selectinload(RecurrenceRecord.road_segment).selectinload(RoadSegment.road),
                selectinload(RecurrenceRecord.related_maintenance_job),
            )
            .order_by(desc(RecurrenceRecord.created_at))
            .limit(limit)
        )
    ).scalars().all()
    out = []
    for r in recs:
        f = r.rule_factors or {}
        pt = wkt_or_geom_to_point(r.new_damage.location) if r.new_damage and r.new_damage.location is not None else None
        seg = r.road_segment
        out.append({
            "id": str(r.id),
            "status": r.status,
            "escalation_level": r.escalation_level,
            "escalation_reasons": r.escalation_reasons or [],
            "historical_damage_id": str(r.historical_damage_id),
            "new_damage_id": str(r.new_damage_id),
            "damage_type": r.new_damage.damage_type.code if r.new_damage and r.new_damage.damage_type else None,
            "new_severity": r.new_damage.severity if r.new_damage else None,
            "location": {"latitude": pt[0], "longitude": pt[1]} if pt else None,
            "road_id": str(seg.road_id) if seg else None,
            "road_name": seg.road.name if seg and seg.road else None,
            "segment_number": seg.segment_number if seg else None,
            "distance_meters": float(r.spatial_distance_meters) if r.spatial_distance_meters is not None else None,
            "days_since_repair": f.get("days_since_repair"),
            "recurrence_number_at_location": f.get("recurrence_number_at_location"),
            "previous_repair_job_id": str(r.related_maintenance_job_id) if r.related_maintenance_job_id else None,
            "previous_repair_job_title": r.related_maintenance_job.title if r.related_maintenance_job else None,
            "previous_verification_result": f.get("previous_verification_result"),
            "previous_verification_source": f.get("previous_verification_source"),
            "detection_method_version": r.detection_method_version,
            "evaluated_at": _iso(r.evaluated_at),
        })
    return out


async def road_intelligence(db: AsyncSession, org_id: uuid.UUID, road_id: uuid.UUID) -> dict[str, Any]:
    road = await db.get(Road, road_id)
    if road is None or road.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "NOT_FOUND", "message": "Road not found."})
    segments = (
        await db.execute(select(RoadSegment).where(RoadSegment.road_id == road.id).order_by(RoadSegment.segment_number))
    ).scalars().all()
    snaps = (
        await db.execute(
            select(RoadHealthSnapshot)
            .where(RoadHealthSnapshot.organization_id == org_id, RoadHealthSnapshot.road_id == road.id)
            .order_by(RoadHealthSnapshot.calculated_at)
        )
    ).scalars().all()
    road_series = [_snapshot(s) for s in snaps if s.road_segment_id is None]
    seg_series: dict[str, list[dict[str, Any]]] = {}
    for s in snaps:
        if s.road_segment_id:
            seg_series.setdefault(str(s.road_segment_id), []).append(_snapshot(s))

    damages = (
        await db.execute(
            select(DamageRecord)
            .where(DamageRecord.organization_id == org_id, DamageRecord.road_id == road.id)
            .options(selectinload(DamageRecord.damage_type))
            .order_by(DamageRecord.created_at)
        )
    ).scalars().all()
    damage_ids = [d.id for d in damages]
    jobs = (
        await db.execute(
            select(MaintenanceJob).where(MaintenanceJob.organization_id == org_id, MaintenanceJob.road_id == road.id)
        )
    ).scalars().all()
    linked_job_ids = set(
        (
            await db.execute(
                select(MaintenanceDamageLink.maintenance_job_id).where(MaintenanceDamageLink.damage_record_id.in_(damage_ids))
            )
        ).scalars()
    ) if damage_ids else set()
    job_ids = {j.id for j in jobs} | linked_job_ids
    if linked_job_ids - {j.id for j in jobs}:
        jobs = list(jobs) + list(
            (await db.execute(select(MaintenanceJob).where(MaintenanceJob.id.in_(linked_job_ids - {j.id for j in jobs})))).scalars()
        )
    inspections = (
        await db.execute(
            select(Inspection).where(Inspection.organization_id == org_id, Inspection.road_id == road.id)
        )
    ).scalars().all()
    reviews = (
        await db.execute(select(DamageReview).where(DamageReview.damage_record_id.in_(damage_ids)))
    ).scalars().all() if damage_ids else []
    history = (
        await db.execute(select(MaintenanceStatusHistory).where(MaintenanceStatusHistory.maintenance_job_id.in_(job_ids)))
    ).scalars().all() if job_ids else []
    evidence = (
        await db.execute(select(RepairEvidence).where(RepairEvidence.maintenance_job_id.in_(job_ids)))
    ).scalars().all() if job_ids else []
    verifications = (
        await db.execute(select(RepairVerification).where(RepairVerification.maintenance_job_id.in_(job_ids)))
    ).scalars().all() if job_ids else []
    recurrences = (
        await db.execute(
            select(RecurrenceRecord).where(
                or_(RecurrenceRecord.new_damage_id.in_(damage_ids), RecurrenceRecord.historical_damage_id.in_(damage_ids))
            )
        )
    ).scalars().all() if damage_ids else []

    events: list[dict[str, Any]] = []

    def add(kind: str, at: datetime | None, title: str, entity_id: Any, **data: Any) -> None:
        if at is not None:
            events.append({"type": kind, "at": _iso(at), "title": title, "entity_id": str(entity_id), "data": data})

    for i in inspections:
        add("INSPECTION", i.captured_at or i.created_at, f"Inspection ({i.status})", i.id, status=i.status)
    for d in damages:
        add("DAMAGE", d.detected_at or d.created_at,
            f"{d.damage_type.code if d.damage_type else 'Damage'} detected ({d.severity})", d.id,
            severity=d.severity, status=d.status, source=d.source_type, observation_count=d.observation_count,
            inspection_id=str(d.inspection_id) if d.inspection_id else None)
    for r in reviews:
        add("DAMAGE_REVIEW", r.reviewed_at, f"Damage review: {r.review_status}", r.damage_record_id,
            original_severity=r.original_severity, reviewed_severity=r.reviewed_severity, notes=r.review_notes)
    for s in snaps:
        add("HEALTH", s.calculated_at,
            f"Health {'segment' if s.road_segment_id else 'road'}: "
            f"{float(s.health_score) if s.health_score is not None else 'insufficient data'} ({s.health_status})",
            s.id, **_snapshot(s))
    for j in jobs:
        add("PRIORITY", j.created_at, f"Maintenance job created · priority {j.priority_level}", j.id,
            priority_level=j.priority_level, priority_score=float(j.priority_score) if j.priority_score is not None else None,
            mode=(j.priority_factors or {}).get("mode"), components=(j.priority_factors or {}).get("components"))
    for h in history:
        add("MAINTENANCE", h.changed_at, f"Maintenance {h.previous_status or '—'} → {h.new_status}", h.maintenance_job_id,
            reason=h.reason)
    for e in evidence:
        add("REPAIR_EVIDENCE", e.created_at, f"Repair evidence uploaded ({e.evidence_type})", e.maintenance_job_id,
            evidence_id=str(e.id), evidence_type=e.evidence_type)
    for v in verifications:
        if v.verification_type == "AUTOMATED_IMAGE_ANALYSIS":
            add("VERIFICATION", v.updated_at if v.verification_status == "COMPLETED" else v.created_at,
                f"Automated image verification: {v.result or v.verification_status}", v.maintenance_job_id,
                verification_id=str(v.id), result=v.result, model=f"{v.model_name} {v.model_version}" if v.model_name else None,
                reason_code=(v.findings or {}).get("reason_code"))
        elif v.verification_type == "HUMAN_REVIEW":
            add("VERIFICATION", v.verified_at, f"Reviewer {v.review_decision}: {v.previous_result} → {v.result}",
                v.maintenance_job_id, verification_id=str(v.id), result=v.result, notes=v.reviewer_notes)
        elif v.verified_by_user_id:
            add("VERIFICATION", v.verified_at or v.created_at, f"Human sign-off: {v.verification_status}",
                v.maintenance_job_id, verification_id=str(v.id), result=v.result)
    for r in recurrences:
        add("RECURRENCE", r.evaluated_at, f"Recurrence {r.status}"
            + (f" · escalation {r.escalation_level}" if r.escalation_level and r.escalation_level != "NONE" else ""),
            r.id, escalation_level=r.escalation_level, reasons=r.escalation_reasons,
            distance_meters=float(r.spatial_distance_meters) if r.spatial_distance_meters is not None else None)
    events.sort(key=lambda e: e["at"])

    latest_by_seg = {sid: series[-1] for sid, series in seg_series.items()}
    return {
        "road": {
            "id": str(road.id), "name": road.name, "road_code": road.road_code, "road_type": road.road_type,
            "traffic_volume_class": road.traffic_volume_class, "traffic_aadt": road.traffic_aadt,
            "traffic_data_source": road.traffic_data_source,
        },
        "segments": [
            {"id": str(s.id), "segment_number": s.segment_number, "name": s.name,
             "length_meters": float(s.length_meters) if s.length_meters is not None else None,
             "latest_health": latest_by_seg.get(str(s.id))}
            for s in segments
        ],
        "road_health_history": road_series,
        "segment_health_history": seg_series,
        "summary": {
            "active_damages": sum(1 for d in damages if d.status in ACTIVE_DAMAGE),
            "pending_review_damages": sum(1 for d in damages if d.status == "PENDING_REVIEW"),
            "repaired_damages": sum(1 for d in damages if d.status == "REPAIRED"),
            "active_by_severity": {
                sev: sum(1 for d in damages if d.status in ACTIVE_DAMAGE and d.severity == sev)
                for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
            },
            "maintenance_by_status": {st: sum(1 for j in jobs if j.status == st) for st in sorted({j.status for j in jobs})},
            "active_recurrences": sum(1 for r in recurrences if r.status in ACTIVE_RECURRENCE),
            "inspections": len(inspections),
        },
        "timeline": events,
    }


LEVEL_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


async def priority_overview(db: AsyncSession, org_id: uuid.UUID) -> list[dict[str, Any]]:
    """Open maintenance jobs ranked by priority, each with the full factor breakdown and the
    context behind it (health, recurrence/escalation, latest rule-based estimate)."""
    from app.models.intelligence import DeteriorationPrediction

    jobs = (
        await db.execute(
            select(MaintenanceJob).where(
                MaintenanceJob.organization_id == org_id, MaintenanceJob.status.not_in(("VERIFIED", "CANCELLED"))
            )
        )
    ).scalars().all()
    out = []
    for j in jobs:
        damages = (
            await db.execute(
                select(DamageRecord)
                .join(MaintenanceDamageLink, MaintenanceDamageLink.damage_record_id == DamageRecord.id)
                .where(MaintenanceDamageLink.maintenance_job_id == j.id)
            )
        ).scalars().all()
        dmg_ids = [d.id for d in damages]
        recs = (
            await db.execute(
                select(RecurrenceRecord.escalation_level).where(
                    RecurrenceRecord.status.in_(ACTIVE_RECURRENCE),
                    or_(RecurrenceRecord.new_damage_id.in_(dmg_ids), RecurrenceRecord.historical_damage_id.in_(dmg_ids)),
                )
            )
        ).scalars().all() if dmg_ids else []
        road = await db.get(Road, j.road_id) if j.road_id else None
        seg = await db.get(RoadSegment, j.road_segment_id) if j.road_segment_id else None
        health = None
        estimate = None
        if seg is not None:
            snap = (
                await db.execute(
                    select(RoadHealthSnapshot)
                    .where(RoadHealthSnapshot.road_segment_id == seg.id)
                    .order_by(desc(RoadHealthSnapshot.calculated_at))
                    .limit(1)
                )
            ).scalar_one_or_none()
            health = _snapshot(snap) if snap else None
            pred = (
                await db.execute(
                    select(DeteriorationPrediction)
                    .where(DeteriorationPrediction.road_segment_id == seg.id, DeteriorationPrediction.status == "GENERATED")
                    .order_by(desc(DeteriorationPrediction.generated_at))
                    .limit(1)
                )
            ).scalar_one_or_none()
            if pred is not None:
                estimate = {
                    "predicted_risk": float(pred.predicted_risk) if pred.predicted_risk is not None else None,
                    "risk_band": (pred.features or {}).get("risk_band"),
                    "horizon_days": pred.prediction_horizon_days,
                    "method": "RULE_BASED_ESTIMATE",
                    "generated_at": _iso(pred.generated_at),
                }
        pf = j.priority_factors or {}
        out.append({
            "job_id": str(j.id),
            "title": j.title,
            "status": j.status,
            "priority_level": j.priority_level,
            "priority_score": float(j.priority_score) if j.priority_score is not None else None,
            "mode": pf.get("mode"),
            "version": pf.get("version"),
            "components": pf.get("components"),
            "inputs": pf.get("inputs"),
            "calculated_at": pf.get("calculated_at"),
            "road_id": str(road.id) if road else None,
            "road_name": road.name if road else None,
            "segment_number": seg.segment_number if seg else None,
            "linked_damage_count": len(damages),
            "max_severity": min((d.severity for d in damages), key=lambda s: LEVEL_ORDER.get(s, 9), default=None),
            "segment_health": health,
            "active_recurrences": len(recs),
            "escalation_level": max(
                (lvl for lvl in recs if lvl), key=lambda lvl: ("NONE", "ELEVATED", "CRITICAL").index(lvl), default=None
            ),
            "deterioration_estimate": estimate,
            "created_at": _iso(j.created_at),
        })
    out.sort(key=lambda x: (LEVEL_ORDER.get(x["priority_level"], 9), -(x["priority_score"] or 0)))
    for rank, item in enumerate(out, 1):
        item["rank"] = rank
    return out
