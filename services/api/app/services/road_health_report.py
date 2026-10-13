"""
Data for the Road Health Assessment Report (the PDF form of the ROAD_HEALTH report).

Everything returned here is read from stored records at generation time: the latest health
snapshot of each road segment (written by health_engine), the open damage records behind those
snapshots, their maintenance jobs and their inspection photos. Nothing is estimated. A value
that is not recorded is returned as None and the PDF says it is not available.

The summary figures follow the same rule as AnalyticsService.get_road_health_analytics: the
latest snapshot per segment, with INSUFFICIENT_DATA segments counted separately and never scored.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.damage import DamageObservation, DamageRecord
from app.models.identity import Organization
from app.models.inspection import InspectionMedia
from app.models.intelligence import RoadHealthSnapshot
from app.models.maintenance import MaintenanceDamageLink, MaintenanceJob
from app.models.road import Road, RoadSegment
from app.services.analytics_service import ACTIVE_DAMAGE_STATUSES
from app.services.health_engine import CALCULATION_VERSION, classify_health_status
from app.services.spatial import geometry_to_geojson, wkt_or_geom_to_point

TIMEFRAME_DAYS = {"last_7_days": 7, "last_30_days": 30, "last_90_days": 90}
TIMEFRAME_LABEL = {
    "last_7_days": "Last 7 days",
    "last_30_days": "Last 30 days",
    "last_90_days": "Last 90 days",
    "all_time": "All recorded history",
}
SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
STATUS_ORDER = {"CRITICAL": 0, "POOR": 1, "FAIR": 2, "GOOD": 3, "INSUFFICIENT_DATA": 4}
CLOSED_JOB_STATUSES = ("VERIFIED", "CANCELLED")
MAX_EVIDENCE_PHOTOS = 6


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


def _iso(dt: datetime | None) -> str | None:
    dt = _utc(dt)
    return dt.isoformat() if dt else None


def _num(value: Any) -> float | None:
    try:
        return None if value is None else float(value)
    except (TypeError, ValueError):
        return None


def _parse_uuid(value: Any) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value)) if value else None
    except (ValueError, TypeError):
        return None


def _segment_label(seg: RoadSegment | None) -> str:
    if seg is None:
        return "Not assigned to a segment"
    label = f"Segment {seg.segment_number}"
    return f"{label} ({seg.name})" if seg.name else label


def _line_coords(geom: Any) -> list[list[float]]:
    """[[lon, lat], ...] of a stored LINESTRING, or [] when there is no usable geometry."""
    gj = geometry_to_geojson(geom)
    if not gj or gj.get("type") != "LineString":
        return []
    out = []
    for pt in gj.get("coordinates") or []:
        try:
            out.append([float(pt[0]), float(pt[1])])
        except (TypeError, ValueError, IndexError):
            continue
    return out if len(out) >= 2 else []


async def build_road_health_detail(
    db: AsyncSession,
    org_id: uuid.UUID,
    parameters: dict[str, Any],
    generated_at: datetime,
    report_id: uuid.UUID,
) -> dict[str, Any]:
    generated_at = _utc(generated_at) or datetime.now(UTC)
    timeframe = str(parameters.get("timeframe") or "all_time")
    days = TIMEFRAME_DAYS.get(timeframe)
    period_start = generated_at - timedelta(days=days) if days else None

    organization = await db.get(Organization, org_id)

    # Optional scope: one road of this organization.
    road_scope: Road | None = None
    road_id = _parse_uuid(parameters.get("road_id"))
    if road_id is not None:
        road_scope = (
            await db.execute(select(Road).where(Road.id == road_id, Road.organization_id == org_id))
        ).scalar_one_or_none()

    # --- latest snapshot per segment (and the snapshot in force at the start of the period)
    snap_stmt = (
        select(RoadHealthSnapshot)
        .where(RoadHealthSnapshot.organization_id == org_id, RoadHealthSnapshot.road_segment_id.is_not(None))
        .options(selectinload(RoadHealthSnapshot.road_segment).selectinload(RoadSegment.road))
        .order_by(RoadHealthSnapshot.calculated_at.desc())
    )
    if road_scope is not None:
        snap_stmt = snap_stmt.where(RoadHealthSnapshot.road_id == road_scope.id)
    snapshots = (await db.execute(snap_stmt)).scalars().all()

    latest: dict[uuid.UUID, RoadHealthSnapshot] = {}
    at_period_start: dict[uuid.UUID, RoadHealthSnapshot] = {}
    for snap in snapshots:  # newest first
        latest.setdefault(snap.road_segment_id, snap)
        calculated = _utc(snap.calculated_at)
        if period_start is not None and calculated is not None and calculated <= period_start:
            at_period_start.setdefault(snap.road_segment_id, snap)

    # --- open damage records (the ones the health score counts)
    dmg_stmt = (
        select(DamageRecord)
        .where(DamageRecord.organization_id == org_id, DamageRecord.status.in_(ACTIVE_DAMAGE_STATUSES))
        .options(
            selectinload(DamageRecord.damage_type),
            selectinload(DamageRecord.road),
            selectinload(DamageRecord.road_segment),
            selectinload(DamageRecord.maintenance_links).selectinload(MaintenanceDamageLink.maintenance_job),
        )
    )
    if road_scope is not None:
        dmg_stmt = dmg_stmt.where(DamageRecord.road_id == road_scope.id)
    damages = list((await db.execute(dmg_stmt)).scalars().all())
    damages.sort(
        key=lambda d: (
            SEVERITY_ORDER.get(str(d.severity).upper(), 9),
            -(_num(d.severity_score) or 0.0),
            str(d.id),
        )
    )

    # Detections awaiting human review are not damage yet and are not part of any score.
    pending_stmt = select(DamageRecord.id).where(
        DamageRecord.organization_id == org_id, DamageRecord.status == "PENDING_REVIEW"
    )
    if road_scope is not None:
        pending_stmt = pending_stmt.where(DamageRecord.road_id == road_scope.id)
    pending_review = len((await db.execute(pending_stmt)).scalars().all())

    # --- one stored inspection photo per defect, for the most severe defects only
    photo_for: dict[uuid.UUID, InspectionMedia] = {}
    top_ids = [d.id for d in damages[: MAX_EVIDENCE_PHOTOS * 3]]
    if top_ids:
        rows = (
            await db.execute(
                select(DamageObservation.damage_record_id, InspectionMedia)
                .join(InspectionMedia, InspectionMedia.id == DamageObservation.media_id)
                .where(
                    DamageObservation.damage_record_id.in_(top_ids),
                    InspectionMedia.media_type == "IMAGE",
                )
                .order_by(DamageObservation.observed_at.asc())
            )
        ).all()
        for damage_id, media in rows:
            photo_for.setdefault(damage_id, media)

    defects: list[dict[str, Any]] = []
    for index, d in enumerate(damages, 1):
        point = wkt_or_geom_to_point(d.location)
        job: MaintenanceJob | None = None
        for link in d.maintenance_links or []:
            candidate = link.maintenance_job
            if candidate is not None and candidate.status not in CLOSED_JOB_STATUSES:
                job = candidate
                break
        media = photo_for.get(d.id)
        defects.append(
            {
                "ref": f"D{index:03d}",
                "type": d.damage_type.name if d.damage_type else "Unclassified",
                "severity": str(d.severity).upper(),
                "status": d.status,
                "source": d.source_type,
                "reviewed": d.reviewed_at is not None,
                "road": d.road.name if d.road else None,
                "segment": _segment_label(d.road_segment),
                "segment_id": str(d.road_segment_id) if d.road_segment_id else None,
                "lat": point[0] if point else None,
                "lon": point[1] if point else None,
                "detected_at": _iso(d.detected_at),
                "confidence": _num(d.confidence),
                "area_m2": _num(d.estimated_area_m2),
                "observations": d.observation_count or 1,
                "job": (
                    {"title": job.title, "status": job.status, "due_at": _iso(job.due_at), "priority": job.priority_level}
                    if job
                    else None
                ),
                "photo": (
                    {"bucket": media.storage_bucket, "path": media.storage_path, "captured_at": _iso(media.captured_at)}
                    if media
                    else None
                ),
            }
        )

    open_by_segment: dict[str, int] = {}
    for item in defects:
        if item["segment_id"]:
            open_by_segment[item["segment_id"]] = open_by_segment.get(item["segment_id"], 0) + 1

    # --- segments
    segments: list[dict[str, Any]] = []
    for seg_id, snap in latest.items():
        seg = snap.road_segment
        road = seg.road if seg is not None else None
        factors = snap.factors or {}
        previous = at_period_start.get(seg_id)
        segments.append(
            {
                "segment_id": str(seg_id),
                "road": road.name if road else "Unknown road",
                "road_code": road.road_code if road else None,
                "area": road.administrative_area if road else None,
                "segment": _segment_label(seg),
                "segment_number": seg.segment_number if seg else None,
                "length_m": _num(seg.length_meters) if seg else None,
                "score": _num(snap.health_score),
                "status": snap.health_status,
                "calculated_at": _iso(snap.calculated_at),
                "version": snap.calculation_version,
                "severity": {k: int(v or 0) for k, v in (factors.get("severity_breakdown") or {}).items()},
                "deductions": {k: _num(v) or 0.0 for k, v in (factors.get("score_deductions") or {}).items()},
                "recurrences": int(factors.get("recurrence_count") or 0),
                "freshness_days": factors.get("inspection_freshness_days"),
                "traffic_class": (factors.get("traffic") or {}).get("traffic_volume_class"),
                "open_defects": open_by_segment.get(str(seg_id), 0),
                "score_at_period_start": _num(previous.health_score) if previous else None,
                "status_at_period_start": previous.health_status if previous else None,
                "line": _line_coords(seg.geometry) if seg is not None else [],
            }
        )
    segments.sort(
        key=lambda s: (STATUS_ORDER.get(s["status"], 9), s["score"] if s["score"] is not None else 101.0, s["road"])
    )

    scored = [s for s in segments if s["score"] is not None]
    distribution = {"GOOD": 0, "FAIR": 0, "POOR": 0, "CRITICAL": 0}
    for s in scored:
        distribution[s["status"]] = distribution.get(s["status"], 0) + 1
    average = round(sum(s["score"] for s in scored) / len(scored), 2) if scored else None

    severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    type_counts: dict[str, int] = {}
    for item in defects:
        severity_counts[item["severity"]] = severity_counts.get(item["severity"], 0) + 1
        type_counts[item["type"]] = type_counts.get(item["type"], 0) + 1

    # --- period figures
    new_in_period = None
    start_scores = [s["score_at_period_start"] for s in segments if s["score_at_period_start"] is not None]
    if period_start is not None:
        new_in_period = sum(
            1 for d in damages if _utc(d.detected_at) is not None and _utc(d.detected_at) >= period_start
        )

    job_stmt = select(MaintenanceJob.status).where(
        MaintenanceJob.organization_id == org_id, MaintenanceJob.status.not_in(CLOSED_JOB_STATUSES)
    )
    if road_scope is not None:
        job_stmt = job_stmt.where(MaintenanceJob.road_id == road_scope.id)
    open_jobs: dict[str, int] = {}
    for (job_status,) in (await db.execute(job_stmt)).all():
        open_jobs[job_status] = open_jobs.get(job_status, 0) + 1

    roads = sorted({s["road"] for s in segments})
    return {
        "report_id": str(report_id),
        "generated_at": generated_at.isoformat(),
        "organization": {
            "name": organization.name if organization else None,
            "code": organization.code if organization else None,
        },
        "scope": {
            "road": road_scope.name if road_scope else None,
            "road_code": road_scope.road_code if road_scope else None,
            "area": road_scope.administrative_area if road_scope else None,
            "requested_road_not_found": road_id is not None and road_scope is None,
            "roads": roads,
        },
        "period": {
            "label": TIMEFRAME_LABEL.get(timeframe, timeframe.replace("_", " ")),
            "start": period_start.isoformat() if period_start else None,
            "end": generated_at.isoformat(),
        },
        "summary": {
            "average_score": average,
            "average_status": classify_health_status(average) if average is not None else None,
            "distribution": distribution,
            "segments_scored": len(scored),
            "segments_insufficient": len(segments) - len(scored),
            "open_defects": len(defects),
            "severity_counts": severity_counts,
            "type_counts": type_counts,
            "pending_review": pending_review,
            "recurrences": sum(s["recurrences"] for s in segments),
            "open_jobs": open_jobs,
        },
        "trend": {
            "new_defects_in_period": new_in_period,
            "segments_with_earlier_score": len(start_scores),
            "average_at_period_start": round(sum(start_scores) / len(start_scores), 2) if start_scores else None,
        },
        "segments": segments,
        "defects": defects,
        "calculation_version": CALCULATION_VERSION,
    }
