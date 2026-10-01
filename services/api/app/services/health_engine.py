import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.damage import DamageRecord
from app.models.history import RecurrenceRecord
from app.models.inspection import Inspection
from app.models.intelligence import RoadHealthSnapshot
from app.models.road import Road, RoadSegment

CALCULATION_VERSION = "health-v1.0.0"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def classify_health_status(score: float | None) -> str:
    if score is None:
        return "INSUFFICIENT_DATA"
    if score >= 80.0:
        return "GOOD"
    if score >= 60.0:
        return "FAIR"
    if score >= 40.0:
        return "POOR"
    return "CRITICAL"


async def calculate_segment_health(
    db: AsyncSession,
    organization_id: uuid.UUID,
    segment: RoadSegment,
    persist: bool = True,
    notes: str | None = None,
) -> RoadHealthSnapshot:
    """Calculate and optionally persist a deterministic, auditable RoadHealthSnapshot for a road segment."""
    # 1. Check for inspection history on this segment or its parent road
    insp_query = select(Inspection).where(
        Inspection.organization_id == organization_id,
        Inspection.status.in_(["SUBMITTED", "PROCESSING", "PROCESSED", "COMPLETED"]),
    )
    if segment.road_id:
        insp_query = insp_query.where(
            (Inspection.road_segment_id == segment.id) | (Inspection.road_id == segment.road_id)
        )
    else:
        insp_query = insp_query.where(Inspection.road_segment_id == segment.id)

    insp_result = await db.execute(insp_query.order_by(desc(Inspection.captured_at)).limit(1))
    latest_inspection = insp_result.scalar_one_or_none()

    # 2. Get active, non-rejected damages on this segment
    damages_query = select(DamageRecord).where(
        DamageRecord.organization_id == organization_id,
        DamageRecord.road_segment_id == segment.id,
        DamageRecord.status.in_(["DETECTED", "CONFIRMED", "MAINTENANCE_SCHEDULED", "IN_PROGRESS"]),
    )
    damages_result = await db.execute(damages_query)
    damages = list(damages_result.scalars().all())

    # 3. Check recurrence records
    recurrence_query = select(func.count(RecurrenceRecord.id)).where(
        RecurrenceRecord.organization_id == organization_id,
        RecurrenceRecord.road_segment_id == segment.id,
    )
    recurrence_count = (await db.execute(recurrence_query)).scalar() or 0

    now = utc_now()
    if segment.length_meters is not None:
        length_m = max(10.0, float(segment.length_meters))
    elif segment.start_chainage is not None and segment.end_chainage is not None:
        length_m = max(10.0, float((segment.end_chainage - segment.start_chainage) * 1000))
    else:
        length_m = 100.0
    length_km = length_m / 1000.0

    if not latest_inspection and len(damages) == 0:
        # Insufficient inspection data
        health_score = None
        health_status = "INSUFFICIENT_DATA"
        factors: dict[str, Any] = {
            "reason": "No inspection or damage data available for segment",
            "damage_density": 0.0,
            "total_damages": 0,
            "severity_breakdown": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "recurrence_count": recurrence_count,
            "inspection_freshness_days": None,
            "score_deductions": {},
        }
    else:
        crit_count = sum(1 for d in damages if str(d.severity).upper() == "CRITICAL")
        high_count = sum(1 for d in damages if str(d.severity).upper() == "HIGH")
        med_count = sum(1 for d in damages if str(d.severity).upper() == "MEDIUM")
        low_count = sum(1 for d in damages if str(d.severity).upper() == "LOW")

        crit_ded = min(60.0, crit_count * 25.0)
        high_ded = min(45.0, high_count * 15.0)
        med_ded = min(35.0, med_count * 7.0)
        low_ded = min(20.0, low_count * 2.5)
        recur_ded = min(25.0, recurrence_count * 5.0)

        total_ded = crit_ded + high_ded + med_ded + low_ded + recur_ded
        computed_score = round(max(0.0, min(100.0, 100.0 - total_ded)), 2)
        health_score = computed_score
        health_status = classify_health_status(health_score)

        insp_captured_at = latest_inspection.captured_at if latest_inspection else None
        if insp_captured_at and insp_captured_at.tzinfo is None:
            insp_captured_at = insp_captured_at.replace(tzinfo=timezone.utc)

        freshness_days = (
            (now - insp_captured_at).days
            if insp_captured_at
            else None
        )
        density = round(len(damages) / length_km, 3)

        factors = {
            "damage_density": density,
            "total_damages": len(damages),
            "severity_breakdown": {
                "critical": crit_count,
                "high": high_count,
                "medium": med_count,
                "low": low_count,
            },
            "recurrence_count": recurrence_count,
            "inspection_freshness_days": freshness_days,
            "score_deductions": {
                "critical": crit_ded,
                "high": high_ded,
                "medium": med_ded,
                "low": low_ded,
                "recurrence": recur_ded,
                "total_deduction": round(total_ded, 2),
            },
        }

    snapshot = RoadHealthSnapshot(
        id=uuid.uuid4(),
        organization_id=organization_id,
        road_id=segment.road_id,
        road_segment_id=segment.id,
        health_score=health_score,
        health_status=health_status,
        calculation_version=CALCULATION_VERSION,
        input_data_timestamp=now,
        factors=factors,
        calculation_metadata={"notes": notes, "length_meters": length_m} if notes else {"length_meters": length_m},
        calculated_at=now,
        created_at=now,
    )

    if persist:
        db.add(snapshot)
        await db.commit()
        await db.refresh(snapshot)

    return snapshot


async def calculate_road_health(
    db: AsyncSession,
    organization_id: uuid.UUID,
    road: Road,
    persist: bool = True,
    notes: str | None = None,
) -> RoadHealthSnapshot:
    """Calculate and optionally persist a health snapshot for an entire road based on its segments."""
    # 1. Fetch segments
    seg_query = select(RoadSegment).where(
        RoadSegment.road_id == road.id,
        RoadSegment.organization_id == organization_id,
        RoadSegment.is_active.is_(True),
    )
    seg_result = await db.execute(seg_query)
    segments = list(seg_result.scalars().all())

    now = utc_now()

    if not segments:
        # Check if direct road inspection/damage exists
        damages_query = select(DamageRecord).where(
            DamageRecord.organization_id == organization_id,
            DamageRecord.road_id == road.id,
            DamageRecord.status.in_(["DETECTED", "CONFIRMED", "MAINTENANCE_SCHEDULED", "IN_PROGRESS"]),
        )
        damages = list((await db.execute(damages_query)).scalars().all())

        if not damages:
            health_score = None
            health_status = "INSUFFICIENT_DATA"
            factors: dict[str, Any] = {
                "reason": "No segments or inspection records for road",
                "total_damages": 0,
                "segment_count": 0,
            }
        else:
            crit_count = sum(1 for d in damages if str(d.severity).upper() == "CRITICAL")
            high_count = sum(1 for d in damages if str(d.severity).upper() == "HIGH")
            med_count = sum(1 for d in damages if str(d.severity).upper() == "MEDIUM")
            low_count = sum(1 for d in damages if str(d.severity).upper() == "LOW")
            total_ded = min(100.0, crit_count * 25.0 + high_count * 15.0 + med_count * 7.0 + low_count * 2.5)
            health_score = round(max(0.0, min(100.0, 100.0 - total_ded)), 2)
            health_status = classify_health_status(health_score)
            factors = {
                "total_damages": len(damages),
                "severity_breakdown": {
                    "critical": crit_count,
                    "high": high_count,
                    "medium": med_count,
                    "low": low_count,
                },
                "segment_count": 0,
            }
    else:
        # Aggregate segments
        scores: list[float] = []
        weights: list[float] = []
        segment_summaries: list[dict[str, Any]] = []

        for seg in segments:
            # Get latest snapshot or compute
            snap_q = select(RoadHealthSnapshot).where(
                RoadHealthSnapshot.road_segment_id == seg.id,
                RoadHealthSnapshot.organization_id == organization_id,
            ).order_by(desc(RoadHealthSnapshot.calculated_at)).limit(1)
            snap = (await db.execute(snap_q)).scalar_one_or_none()

            if snap is None:
                snap = await calculate_segment_health(db, organization_id, seg, persist=persist)

            if seg.length_meters is not None:
                seg_len = max(10.0, float(seg.length_meters))
            elif seg.start_chainage is not None and seg.end_chainage is not None:
                seg_len = max(10.0, float((seg.end_chainage - seg.start_chainage) * 1000))
            else:
                seg_len = 100.0

            segment_summaries.append({
                "segment_id": str(seg.id),
                "segment_number": seg.segment_number,
                "name": seg.name,
                "health_score": float(snap.health_score) if snap.health_score is not None else None,
                "health_status": snap.health_status,
                "length_meters": seg_len,
            })

            if snap.health_score is not None:
                scores.append(float(snap.health_score))
                weights.append(seg_len)

        if not scores:
            health_score = None
            health_status = "INSUFFICIENT_DATA"
            factors = {
                "reason": "All segments lack sufficient inspection data",
                "segment_count": len(segments),
                "segments": segment_summaries,
            }
        else:
            total_weight = sum(weights)
            weighted_score = sum(s * w for s, w in zip(scores, weights)) / total_weight if total_weight > 0 else sum(scores) / len(scores)
            health_score = round(max(0.0, min(100.0, weighted_score)), 2)
            health_status = classify_health_status(health_score)
            factors = {
                "segment_count": len(segments),
                "segments_with_data": len(scores),
                "average_segment_score": round(sum(scores) / len(scores), 2),
                "segments": segment_summaries,
            }

    road_snapshot = RoadHealthSnapshot(
        id=uuid.uuid4(),
        organization_id=organization_id,
        road_id=road.id,
        road_segment_id=None,
        health_score=health_score,
        health_status=health_status,
        calculation_version=CALCULATION_VERSION,
        input_data_timestamp=now,
        factors=factors,
        calculation_metadata={"notes": notes} if notes else None,
        calculated_at=now,
        created_at=now,
    )

    if persist:
        db.add(road_snapshot)
        await db.commit()
        await db.refresh(road_snapshot)

    return road_snapshot
