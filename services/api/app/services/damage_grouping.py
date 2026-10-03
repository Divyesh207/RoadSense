"""
GPS-based grouping of damage observations across inspections.

A promoted AI detection is attached to an existing OPEN damage record when both:
  - the damage type is the same (unrelated nearby damage is never merged), and
  - the detection lies within DAMAGE_GROUPING_RADIUS_METERS of the record
    (PostGIS ST_DWithin on geography, i.e. metres on the WGS84 spheroid).

Distinct detections from the SAME image share the photo's GPS point, so a record
never absorbs a second detection from a media item it already has an observation
for: those are different physical damages in one photo. Within-video duplicates
are already removed by the worker before detections are stored.

Every sighting is kept as a DamageObservation (inspection -> media -> detection ->
damage record); records are never merged or deleted.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from geoalchemy2 import Geography
from sqlalchemy import cast, exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.ai import AIDetection
from app.models.damage import DamageObservation, DamageRecord
from app.services.spatial import haversine_distance_m, wkt_or_geom_to_point
from app.services.spatial_queries import is_postgres

# Statuses of damage that is still physically present and unresolved. REJECTED (not
# damage) and REPAIRED (fixed; a new sighting is a recurrence candidate) are excluded.
OPEN_DAMAGE_STATUSES = ("DETECTED", "PENDING_REVIEW", "CONFIRMED", "MAINTENANCE_SCHEDULED", "IN_PROGRESS")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class PromotionResult:
    record: DamageRecord
    action: str  # CREATED | GPS_GROUPED | ALREADY_PROMOTED
    distance_meters: float | None = None


async def _postgis_match(
    db: AsyncSession, organization_id: uuid.UUID, damage_type_id: uuid.UUID, lat: float, lon: float,
    media_id: uuid.UUID | None, radius_m: float,
) -> tuple[DamageRecord, float] | None:
    target = cast(func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326), Geography)
    record_geog = cast(DamageRecord.location, Geography)
    distance = func.ST_Distance(record_geog, target)
    stmt = (
        select(DamageRecord, distance.label("distance_m"))
        .where(
            DamageRecord.organization_id == organization_id,
            DamageRecord.damage_type_id == damage_type_id,
            DamageRecord.status.in_(OPEN_DAMAGE_STATUSES),
            DamageRecord.location.is_not(None),
            func.ST_DWithin(record_geog, target, radius_m),
        )
        .order_by(distance, DamageRecord.created_at)
        .limit(1)
    )
    if media_id is not None:
        stmt = stmt.where(
            ~exists().where(
                DamageObservation.damage_record_id == DamageRecord.id,
                DamageObservation.media_id == media_id,
            )
        )
    row = (await db.execute(stmt)).first()
    return (row[0], float(row[1])) if row else None


async def _portable_match(
    db: AsyncSession, organization_id: uuid.UUID, damage_type_id: uuid.UUID, lat: float, lon: float,
    media_id: uuid.UUID | None, radius_m: float,
) -> tuple[DamageRecord, float] | None:
    """Same rule evaluated in Python; used only where PostGIS is unavailable (SQLite unit tests)."""
    stmt = select(DamageRecord).where(
        DamageRecord.organization_id == organization_id,
        DamageRecord.damage_type_id == damage_type_id,
        DamageRecord.status.in_(OPEN_DAMAGE_STATUSES),
        DamageRecord.location.is_not(None),
    )
    if media_id is not None:
        stmt = stmt.where(
            ~exists().where(
                DamageObservation.damage_record_id == DamageRecord.id,
                DamageObservation.media_id == media_id,
            )
        )
    best: tuple[DamageRecord, float] | None = None
    for record in (await db.execute(stmt)).scalars():
        coords = wkt_or_geom_to_point(record.location)
        if coords is None:
            continue
        d = haversine_distance_m(lat, lon, coords[0], coords[1])
        if d <= radius_m and (best is None or d < best[1]):
            best = (record, d)
    return best


async def find_matching_damage(
    db: AsyncSession, organization_id: uuid.UUID, damage_type_id: uuid.UUID, lat: float, lon: float,
    media_id: uuid.UUID | None = None, radius_m: float | None = None,
) -> tuple[DamageRecord, float] | None:
    radius = settings.DAMAGE_GROUPING_RADIUS_METERS if radius_m is None else radius_m
    if is_postgres(db):
        return await _postgis_match(db, organization_id, damage_type_id, lat, lon, media_id, radius)
    return await _portable_match(db, organization_id, damage_type_id, lat, lon, media_id, radius)


async def _already_promoted(db: AsyncSession, organization_id: uuid.UUID, detection_id: uuid.UUID) -> DamageRecord | None:
    stmt = (
        select(DamageRecord)
        .outerjoin(DamageObservation, DamageObservation.damage_record_id == DamageRecord.id)
        .where(
            DamageRecord.organization_id == organization_id,
            (DamageObservation.detection_id == detection_id) | (DamageRecord.source_detection_id == detection_id),
        )
        .limit(1)
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def promote_detection(db: AsyncSession, organization_id: uuid.UUID, det: AIDetection) -> PromotionResult:
    """Promote an AI detection to a canonical damage record, grouping by GPS when it matches
    an open record of the same type. Idempotent per detection. Commits."""
    existing = await _already_promoted(db, organization_id, det.id)
    if existing is not None:
        return PromotionResult(existing, "ALREADY_PROMOTED")

    insp = det.inspection
    location = det.location or (insp.location if insp else None)
    observed_at = det.created_at or utc_now()
    coords = wkt_or_geom_to_point(location) if location is not None else None

    match = None
    if coords is not None:
        match = await find_matching_damage(db, organization_id, det.damage_type_id, coords[0], coords[1], det.media_id)

    if match is not None:
        record, distance = match
        record.observation_count = (record.observation_count or 1) + 1
        current_last = record.last_observed_at
        if current_last is not None and current_last.tzinfo is None:
            current_last = current_last.replace(tzinfo=timezone.utc)
        obs_at = observed_at if observed_at.tzinfo else observed_at.replace(tzinfo=timezone.utc)
        record.last_observed_at = max(current_last, obs_at) if current_last else obs_at
        record.updated_at = utc_now()
        action = "GPS_GROUPED"
    else:
        sev_info = (det.raw_output or {}).get("severity_assessment", {})
        record = DamageRecord(
            id=uuid.uuid4(),
            organization_id=organization_id,
            inspection_id=det.inspection_id,
            source_detection_id=det.id,
            road_id=insp.road_id if insp else None,
            road_segment_id=insp.road_segment_id if insp else None,
            damage_type_id=det.damage_type_id,
            source_type="AI",
            severity=sev_info.get("severity", "MEDIUM"),
            severity_score=sev_info.get("score"),
            severity_method_version="1.0.0",
            location=location,
            status="PENDING_REVIEW",
            confidence=det.confidence,
            # Physical area cannot be derived from a bounding box without camera
            # calibration; it is left unset rather than guessed.
            estimated_area_m2=None,
            detected_at=det.created_at,
            observation_count=1,
            last_observed_at=observed_at,
            created_at=utc_now(),
        )
        db.add(record)
        distance = None
        action = "CREATED"

    db.add(
        DamageObservation(
            id=uuid.uuid4(),
            organization_id=organization_id,
            damage_record_id=record.id,
            detection_id=det.id,
            inspection_id=det.inspection_id,
            media_id=det.media_id,
            match_method="GPS_GROUPED" if action == "GPS_GROUPED" else "NEW_RECORD",
            distance_meters=round(distance, 3) if distance is not None else None,
            location=location,
            observed_at=observed_at,
            created_at=utc_now(),
        )
    )
    try:
        await db.commit()
    except IntegrityError:
        # A concurrent request promoted the same detection (unique detection_id).
        await db.rollback()
        existing = await _already_promoted(db, organization_id, det.id)
        if existing is None:
            raise
        return PromotionResult(existing, "ALREADY_PROMOTED")
    return PromotionResult(record, action, distance)


def manual_observation(record: DamageRecord) -> DamageObservation:
    """Observation row for a manually entered damage record (no detection)."""
    return DamageObservation(
        id=uuid.uuid4(),
        organization_id=record.organization_id,
        damage_record_id=record.id,
        detection_id=None,
        inspection_id=record.inspection_id,
        media_id=None,
        match_method="MANUAL",
        distance_meters=None,
        location=record.location,
        observed_at=record.detected_at or utc_now(),
        created_at=utc_now(),
    )
