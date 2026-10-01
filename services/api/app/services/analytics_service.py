import uuid
from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ai import DamageType
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


def ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class AnalyticsService:

    @staticmethod
    async def get_dashboard_summary(db: AsyncSession, org_id: uuid.UUID) -> DashboardSummaryData:
        # Total Roads
        roads_q = select(func.count(Road.id)).where(Road.organization_id == org_id)
        total_roads = (await db.execute(roads_q)).scalar() or 0

        # Total Segments
        segs_q = select(func.count(RoadSegment.id)).where(RoadSegment.organization_id == org_id)
        total_segments = (await db.execute(segs_q)).scalar() or 0

        # Active Inspections
        active_insp_q = select(func.count(Inspection.id)).where(
            Inspection.organization_id == org_id,
            Inspection.status.in_(["DRAFT", "SUBMITTED", "PROCESSING"])
        )
        active_inspections = (await db.execute(active_insp_q)).scalar() or 0

        # Open damages
        open_dmg_q = select(func.count(DamageRecord.id)).where(
            DamageRecord.organization_id == org_id,
            DamageRecord.status.in_(["DETECTED", "CONFIRMED"])
        )
        open_damages = (await db.execute(open_dmg_q)).scalar() or 0

        # High & Critical severity damages
        high_dmg_q = select(func.count(DamageRecord.id)).where(
            DamageRecord.organization_id == org_id,
            DamageRecord.status.in_(["DETECTED", "CONFIRMED"]),
            DamageRecord.severity == "HIGH"
        )
        high_severity_damages = (await db.execute(high_dmg_q)).scalar() or 0

        crit_dmg_q = select(func.count(DamageRecord.id)).where(
            DamageRecord.organization_id == org_id,
            DamageRecord.status.in_(["DETECTED", "CONFIRMED"]),
            DamageRecord.severity == "CRITICAL"
        )
        critical_damages = (await db.execute(crit_dmg_q)).scalar() or 0

        # Maintenance counts
        maint_open_q = select(func.count(MaintenanceJob.id)).where(
            MaintenanceJob.organization_id == org_id,
            MaintenanceJob.status.in_(["OPEN", "PLANNED"])
        )
        maintenance_open = (await db.execute(maint_open_q)).scalar() or 0

        maint_prog_q = select(func.count(MaintenanceJob.id)).where(
            MaintenanceJob.organization_id == org_id,
            MaintenanceJob.status.in_(["SCHEDULED", "IN_PROGRESS"])
        )
        maintenance_in_progress = (await db.execute(maint_prog_q)).scalar() or 0

        maint_verif_pending_q = select(func.count(RepairVerification.id)).where(
            RepairVerification.organization_id == org_id,
            RepairVerification.verification_status == "PENDING"
        )
        verification_pending = (await db.execute(maint_verif_pending_q)).scalar() or 0

        maint_verified_q = select(func.count(MaintenanceJob.id)).where(
            MaintenanceJob.organization_id == org_id,
            MaintenanceJob.verified_at.isnot(None)
        )
        verified_repairs = (await db.execute(maint_verified_q)).scalar() or 0

        # Recurrences
        rec_q = select(func.count(RecurrenceRecord.id)).where(
            RecurrenceRecord.organization_id == org_id,
            RecurrenceRecord.status.in_(["POTENTIAL", "CONFIRMED"])
        )
        recurrence_count = (await db.execute(rec_q)).scalar() or 0

        # Average road health
        health_q = select(func.avg(RoadHealthSnapshot.health_score)).where(
            RoadHealthSnapshot.organization_id == org_id
        )
        avg_health = (await db.execute(health_q)).scalar()
        avg_health_float = float(avg_health) if avg_health is not None else None

        return DashboardSummaryData(
            total_roads=total_roads,
            total_segments=total_segments,
            active_inspections=active_inspections,
            open_damages=open_damages,
            high_severity_damages=high_severity_damages,
            critical_damages=critical_damages,
            maintenance_open=maintenance_open,
            maintenance_in_progress=maintenance_in_progress,
            verification_pending=verification_pending,
            verified_repairs=verified_repairs,
            recurrence_count=recurrence_count,
            average_road_health=avg_health_float
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
        # Get latest snapshots
        stmt = (
            select(RoadHealthSnapshot)
            .where(RoadHealthSnapshot.organization_id == org_id)
            .options(
                selectinload(RoadHealthSnapshot.road_segment).selectinload(RoadSegment.road)
            )
            .order_by(RoadHealthSnapshot.calculated_at.desc())
        )
        snapshots = (await db.execute(stmt)).scalars().all()

        # Deduplicate to latest snapshot per segment
        seen_segs: set[uuid.UUID] = set()
        latest_snapshots: list[RoadHealthSnapshot] = []
        for s in snapshots:
            if s.road_segment_id and s.road_segment_id not in seen_segs:
                seen_segs.add(s.road_segment_id)
                latest_snapshots.append(s)

        distribution = {"GOOD": 0, "FAIR": 0, "POOR": 0, "CRITICAL": 0}
        total_score = 0.0
        critical_segments: list[CriticalSegmentSummary] = []

        for s in latest_snapshots:
            score = float(s.health_score) if s.health_score is not None else 100.0
            total_score += score

            classification = s.health_status or (
                "GOOD" if score >= 80 else "FAIR" if score >= 60 else "POOR" if score >= 40 else "CRITICAL"
            )
            distribution[classification] = distribution.get(classification, 0) + 1

            if classification == "CRITICAL" or score < 40:
                road_name = s.road_segment.road.name if s.road_segment and s.road_segment.road else "Unknown Road"
                seg_num = s.road_segment.segment_number if s.road_segment else 0
                road_id = s.road_segment.road_id if s.road_segment else uuid.uuid4()
                critical_segments.append(
                    CriticalSegmentSummary(
                        segment_id=s.road_segment_id or uuid.uuid4(),
                        road_id=road_id,
                        road_name=road_name,
                        segment_number=seg_num,
                        current_health_score=score,
                        classification=classification,
                        open_damages_count=0
                    )
                )

        avg_health = (total_score / len(latest_snapshots)) if latest_snapshots else None

        return RoadHealthAnalyticsData(
            average_health=round(avg_health, 2) if avg_health is not None else None,
            health_distribution=distribution,
            critical_segments=critical_segments,
            total_segments_evaluated=len(latest_snapshots)
        )

    @staticmethod
    async def get_maintenance_analytics(db: AsyncSession, org_id: uuid.UUID) -> MaintenanceAnalyticsData:
        # All jobs for org
        stmt = select(MaintenanceJob).where(MaintenanceJob.organization_id == org_id)
        jobs = (await db.execute(stmt)).scalars().all()

        open_cnt = 0
        in_prog_cnt = 0
        comp_cnt = 0
        verified_cnt = 0
        rejected_cnt = 0
        completion_days_list: list[float] = []

        for j in jobs:
            st = j.status
            if st in ["OPEN", "PLANNED"]:
                open_cnt += 1
            elif st in ["SCHEDULED", "IN_PROGRESS"]:
                in_prog_cnt += 1
            elif st == "COMPLETED":
                comp_cnt += 1

            if j.completed_at and j.created_at:
                diff_sec = (ensure_utc(j.completed_at) - ensure_utc(j.created_at)).total_seconds()
                completion_days_list.append(max(0.0, diff_sec / 86400.0))

        # Verifications
        verif_stmt = (
            select(RepairVerification.verification_status, func.count(RepairVerification.id))
            .where(RepairVerification.organization_id == org_id)
            .group_by(RepairVerification.verification_status)
        )
        verif_counts = dict((await db.execute(verif_stmt)).all())
        verified_cnt = verif_counts.get("VERIFIED", 0)
        rejected_cnt = verif_counts.get("REJECTED", 0)

        # Recurrence count after repair
        rec_q = select(func.count(RecurrenceRecord.id)).where(
            RecurrenceRecord.organization_id == org_id,
            RecurrenceRecord.related_maintenance_job_id.isnot(None),
            RecurrenceRecord.status.in_(["POTENTIAL", "CONFIRMED"])
        )
        rec_after_repair = (await db.execute(rec_q)).scalar() or 0

        total_decisions = verified_cnt + rejected_cnt
        verif_rate = (verified_cnt / total_decisions) if total_decisions > 0 else 0.0
        avg_days = (sum(completion_days_list) / len(completion_days_list)) if completion_days_list else None

        return MaintenanceAnalyticsData(
            open_jobs=open_cnt,
            in_progress_jobs=in_prog_cnt,
            completed_jobs=comp_cnt,
            verified_repairs=verified_cnt,
            rejected_repairs=rejected_cnt,
            verification_rate=round(verif_rate, 4),
            avg_completion_time_days=round(avg_days, 2) if avg_days is not None else None,
            recurrence_after_repair_count=rec_after_repair
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
