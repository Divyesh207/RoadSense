import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.damage import DamageRecord
from app.models.history import RecurrenceRecord
from app.models.inspection import Inspection, InspectionMedia
from app.models.intelligence import RoadHealthSnapshot
from app.models.maintenance import MaintenanceJob
from app.models.repair import RepairVerification
from app.models.road import Road, RoadSegment
from app.schemas.analytics import (
    CriticalSegmentSummary,
    DamageTrendPoint,
    DamageTrendsData,
    DashboardSummaryData,
    InspectionAnalyticsData,
    MaintenanceAnalyticsData,
    RoadHealthAnalyticsData,
)

# Confirmed or in the maintenance workflow (unreviewed AI candidates are PENDING_REVIEW).
ACTIVE_DAMAGE_STATUSES = ["DETECTED", "CONFIRMED", "MAINTENANCE_SCHEDULED", "IN_PROGRESS"]


async def latest_road_snapshots(db: AsyncSession, org_id: uuid.UUID) -> list[RoadHealthSnapshot]:
    """Latest road-level (segment_id NULL) snapshot per road."""
    snaps = (
        await db.execute(
            select(RoadHealthSnapshot)
            .where(RoadHealthSnapshot.organization_id == org_id, RoadHealthSnapshot.road_segment_id.is_(None))
            .order_by(RoadHealthSnapshot.calculated_at.desc())
        )
    ).scalars().all()
    seen: set[uuid.UUID] = set()
    out = []
    for snap in snaps:
        if snap.road_id not in seen:
            seen.add(snap.road_id)
            out.append(snap)
    return out


async def final_result_counts(db: AsyncSession, org_id: uuid.UUID) -> dict[str, int]:
    """Final repair-verification outcome per maintenance job (latest human decision, else
    latest completed automated analysis); jobs with neither are not counted."""
    from app.services.recurrence_engine import final_verification

    job_ids = (
        await db.execute(
            select(RepairVerification.maintenance_job_id)
            .where(RepairVerification.organization_id == org_id)
            .distinct()
        )
    ).scalars().all()
    counts: dict[str, int] = {}
    for job_id in job_ids:
        _, result, _ = await final_verification(db, job_id)
        if result:
            counts[result] = counts.get(result, 0) + 1
    return counts


def ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class AnalyticsService:

    @staticmethod
    async def get_dashboard_summary(db: AsyncSession, org_id: uuid.UUID) -> DashboardSummaryData:
        """Every value is a count/average over stored records; nothing is estimated."""

        async def count(model, *where) -> int:
            return (await db.execute(select(func.count(model.id)).where(model.organization_id == org_id, *where))).scalar() or 0

        total_roads = await count(Road)
        total_segments = await count(RoadSegment)
        active_inspections = await count(Inspection, Inspection.status.in_(["DRAFT", "UPLOADING", "SUBMITTED", "PROCESSING"]))
        open_damages = await count(DamageRecord, DamageRecord.status.in_(ACTIVE_DAMAGE_STATUSES))
        pending_review = await count(DamageRecord, DamageRecord.status == "PENDING_REVIEW")
        high = await count(DamageRecord, DamageRecord.status.in_(ACTIVE_DAMAGE_STATUSES), DamageRecord.severity == "HIGH")
        critical = await count(
            DamageRecord, DamageRecord.status.in_(ACTIVE_DAMAGE_STATUSES), DamageRecord.severity == "CRITICAL"
        )
        by_status = dict(
            (
                await db.execute(
                    select(MaintenanceJob.status, func.count(MaintenanceJob.id))
                    .where(MaintenanceJob.organization_id == org_id)
                    .group_by(MaintenanceJob.status)
                )
            ).all()
        )
        verified_repairs = await count(MaintenanceJob, MaintenanceJob.status == "VERIFIED")
        active_rec = RecurrenceRecord.status.in_(["POTENTIAL", "CONFIRMED"])
        recurrence_count = await count(RecurrenceRecord, active_rec)
        escalated = await count(RecurrenceRecord, active_rec, RecurrenceRecord.escalation_level.in_(["ELEVATED", "CRITICAL"]))

        latest_road = await latest_road_snapshots(db, org_id)
        scored = [float(snap.health_score) for snap in latest_road if snap.health_score is not None]
        status_counts: dict[str, int] = {}
        for snap in latest_road:
            status_counts[snap.health_status] = status_counts.get(snap.health_status, 0) + 1

        return DashboardSummaryData(
            total_roads=total_roads,
            total_segments=total_segments,
            active_inspections=active_inspections,
            open_damages=open_damages,
            high_severity_damages=high,
            critical_damages=critical,
            maintenance_open=by_status.get("OPEN", 0),
            maintenance_in_progress=by_status.get("IN_PROGRESS", 0),
            verification_pending=by_status.get("VERIFICATION_PENDING", 0),
            verified_repairs=verified_repairs,
            recurrence_count=recurrence_count,
            average_road_health=round(sum(scored) / len(scored), 2) if scored else None,
            pending_review_damages=pending_review,
            maintenance_by_status=by_status,
            escalated_recurrences=escalated,
            roads_with_health=len(scored),
            road_health_status_counts=status_counts,
            repair_verification_results=await final_result_counts(db, org_id),
        )

    @staticmethod
    async def get_damage_trends(
        db: AsyncSession,
        org_id: uuid.UUID,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        road_id: uuid.UUID | None = None,
        damage_type: str | None = None,
        severity: str | None = None
    ) -> DamageTrendsData:
        stmt = select(DamageRecord).where(DamageRecord.organization_id == org_id).options(
            selectinload(DamageRecord.damage_type)
        )

        if road_id:
            stmt = stmt.where(DamageRecord.road_id == road_id)
        if severity:
            stmt = stmt.where(DamageRecord.severity == severity.upper())

        records = (await db.execute(stmt)).scalars().all()

        from_utc = ensure_utc(from_date)
        to_utc = ensure_utc(to_date)

        by_date: dict[str, dict[str, int]] = {}
        by_type: dict[str, int] = {}
        by_severity: dict[str, int] = {}
        total = 0

        for r in records:
            dt = ensure_utc(r.created_at)
            if from_utc and dt and dt < from_utc:
                continue
            if to_utc and dt and dt > to_utc:
                continue

            # Filter damage_type code if given
            type_code = r.damage_type.code if r.damage_type else "UNKNOWN"
            if damage_type and type_code.upper() != damage_type.upper():
                continue

            total += 1
            by_type[type_code] = by_type.get(type_code, 0) + 1

            sev = r.severity or "UNKNOWN"
            by_severity[sev] = by_severity.get(sev, 0) + 1

            date_key = dt.strftime("%Y-%m-%d") if dt else "UNKNOWN"
            if date_key not in by_date:
                by_date[date_key] = {"total": 0}
            by_date[date_key]["total"] += 1
            by_date[date_key][sev] = by_date[date_key].get(sev, 0) + 1

        series = [
            DamageTrendPoint(
                date=k,
                count=v["total"],
                severity_breakdown={sk: sv for sk, sv in v.items() if sk != "total"}
            )
            for k, v in sorted(by_date.items())
        ]

        return DamageTrendsData(
            series=series,
            by_type=by_type,
            by_severity=by_severity,
            total_damages=total
        )

    @staticmethod
    async def get_road_health_analytics(db: AsyncSession, org_id: uuid.UUID) -> RoadHealthAnalyticsData:
        """Latest snapshot per segment. INSUFFICIENT_DATA segments are counted separately and
        never given a score."""
        snapshots = (
            await db.execute(
                select(RoadHealthSnapshot)
                .where(RoadHealthSnapshot.organization_id == org_id, RoadHealthSnapshot.road_segment_id.is_not(None))
                .options(selectinload(RoadHealthSnapshot.road_segment).selectinload(RoadSegment.road))
                .order_by(RoadHealthSnapshot.calculated_at.desc())
            )
        ).scalars().all()
        seen: set[uuid.UUID] = set()
        latest = []
        for snap in snapshots:
            if snap.road_segment_id not in seen:
                seen.add(snap.road_segment_id)
                latest.append(snap)

        distribution = {"GOOD": 0, "FAIR": 0, "POOR": 0, "CRITICAL": 0}
        scores: list[float] = []
        insufficient = 0
        critical_segments: list[CriticalSegmentSummary] = []
        for snap in latest:
            if snap.health_score is None:
                insufficient += 1
                continue
            score = float(snap.health_score)
            scores.append(score)
            distribution[snap.health_status] = distribution.get(snap.health_status, 0) + 1
            seg = snap.road_segment
            if snap.health_status == "CRITICAL" and seg is not None:
                open_cnt = (
                    await db.execute(
                        select(func.count(DamageRecord.id)).where(
                            DamageRecord.road_segment_id == seg.id, DamageRecord.status.in_(ACTIVE_DAMAGE_STATUSES)
                        )
                    )
                ).scalar() or 0
                critical_segments.append(
                    CriticalSegmentSummary(
                        segment_id=seg.id,
                        road_id=seg.road_id,
                        road_name=seg.road.name if seg.road else "",
                        segment_number=seg.segment_number,
                        current_health_score=score,
                        classification=snap.health_status,
                        open_damages_count=open_cnt,
                    )
                )
        return RoadHealthAnalyticsData(
            average_health=round(sum(scores) / len(scores), 2) if scores else None,
            health_distribution=distribution,
            critical_segments=critical_segments,
            total_segments_evaluated=len(scores),
            segments_insufficient_data=insufficient,
        )

    @staticmethod
    async def get_maintenance_analytics(db: AsyncSession, org_id: uuid.UUID) -> MaintenanceAnalyticsData:
        jobs = (await db.execute(select(MaintenanceJob).where(MaintenanceJob.organization_id == org_id))).scalars().all()
        by_status: dict[str, int] = {}
        completion_days: list[float] = []
        for j in jobs:
            by_status[j.status] = by_status.get(j.status, 0) + 1
            if j.completed_at and j.created_at:
                diff = (ensure_utc(j.completed_at) - ensure_utc(j.created_at)).total_seconds()
                completion_days.append(max(0.0, diff / 86400.0))
        verified = by_status.get("VERIFIED", 0)
        rejected = by_status.get("REJECTED", 0)
        rec_after_repair = (
            await db.execute(
                select(func.count(RecurrenceRecord.id)).where(
                    RecurrenceRecord.organization_id == org_id,
                    RecurrenceRecord.related_maintenance_job_id.isnot(None),
                    RecurrenceRecord.status.in_(["POTENTIAL", "CONFIRMED"]),
                )
            )
        ).scalar() or 0
        decisions = verified + rejected
        return MaintenanceAnalyticsData(
            open_jobs=by_status.get("OPEN", 0),
            in_progress_jobs=by_status.get("IN_PROGRESS", 0),
            completed_jobs=by_status.get("COMPLETED", 0),
            verified_repairs=verified,
            rejected_repairs=rejected,
            verification_rate=round(verified / decisions, 4) if decisions else 0.0,
            avg_completion_time_days=round(sum(completion_days) / len(completion_days), 2) if completion_days else None,
            recurrence_after_repair_count=rec_after_repair,
            by_status=by_status,
            verification_pending_jobs=by_status.get("VERIFICATION_PENDING", 0),
        )

    @staticmethod
    async def get_inspection_analytics(db: AsyncSession, org_id: uuid.UUID) -> InspectionAnalyticsData:
        # Inspections
        stmt = select(Inspection).where(Inspection.organization_id == org_id)
        inspections = (await db.execute(stmt)).scalars().all()

        by_status: dict[str, int] = {}
        ai_processed = 0

        for insp in inspections:
            st = insp.status or "DRAFT"
            by_status[st] = by_status.get(st, 0) + 1
            if st in ["ANALYZED", "REVIEW_REQUIRED", "REVIEWED", "COMPLETED"]:
                ai_processed += 1

        # Media total
        media_q = (
            select(func.count(InspectionMedia.id))
            .join(Inspection, InspectionMedia.inspection_id == Inspection.id)
            .where(Inspection.organization_id == org_id)
        )
        total_media = (await db.execute(media_q)).scalar() or 0

        return InspectionAnalyticsData(
            total_inspections=len(inspections),
            by_status=by_status,
            total_media_captured=total_media,
            ai_processed_count=ai_processed
        )
