import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import AIModel
from app.models.damage import DamageRecord
from app.models.history import RecurrenceRecord
from app.models.inspection import Inspection
from app.models.intelligence import DeteriorationPrediction, RoadHealthSnapshot
from app.models.road import RoadSegment

# Deterioration estimate provenance. This is a deterministic, hand-weighted rule
# set, NOT a trained model: there is no learned artifact, training data or
# evaluation. A trained regressor (e.g. XGBoost) can replace it later behind the
# same API by registering a new AIModel and setting ESTIMATION_METHOD accordingly.
MODEL_NAME = "Rule-Based-Deterioration-Estimate"
MODEL_VERSION = "rules-v2"
MODEL_FAMILY = "RULE_BASED"
ESTIMATION_METHOD = "RULE_BASED_ESTIMATE"
FEATURE_VERSION = "feat-v2.0.0"
# A trainable regressor needs observed outcomes: segments whose health was measured at
# least twice, ML_MIN_SPAN_DAYS apart. Below ML_MIN_TRAINING_SEGMENTS such segments no
# model is trained and the estimate stays rule-based (see ml_training_readiness()).
ML_MIN_TRAINING_SEGMENTS = 30
ML_MIN_SPAN_DAYS = 30
TREND_MIN_SPAN_DAYS = 7
TREND_WINDOW_DAYS = 365
INACTIVE_RECURRENCE = ("DISMISSED", "FALSE_POSITIVE")
RULE_BASED_DISCLAIMER = (
    "Rule-based deterioration estimate from hand-weighted factors (damage severity, current health, "
    "observed health trend, recurrence and escalation, previous repair verification, inspection age, "
    "documented traffic). It is not a trained or validated model, has no statistical confidence, and "
    "must not be treated as a guaranteed future outcome. A future health value is shown only when an "
    "observed health trend exists, as a linear extrapolation of that trend."
)


def utc_now() -> datetime:
    return datetime.now(UTC)


async def get_or_create_prediction_model(db: AsyncSession) -> AIModel:
    """Ensure the deterioration prediction AIModel metadata record exists."""
    q = select(AIModel).where(
        AIModel.name == MODEL_NAME,
        AIModel.version == MODEL_VERSION,
    )
    model = (await db.execute(q)).scalar_one_or_none()
    if model is None:
        model = AIModel(
            id=uuid.uuid4(),
            name=MODEL_NAME,
            model_family=MODEL_FAMILY,
            model_type="DETERIORATION_PREDICTION",
            version=MODEL_VERSION,
            artifact_uri="builtin://app/services/prediction_engine.py#predict_segment_deterioration",
            framework="python-rules",
            status="ACTIVE",
            metadata_={
                "trained": False,
                "description": "Hand-weighted rules over damage severity, health and its observed trend, "
                "recurrence/escalation, repair verification history, inspection age and documented traffic. "
                "Not a trained or evaluated model; no accuracy metrics exist.",
                "feature_version": FEATURE_VERSION,
            },
            created_at=utc_now(),
        )
        db.add(model)
        await db.commit()
        await db.refresh(model)
    return model


async def predict_segment_deterioration(
    db: AsyncSession,
    organization_id: uuid.UUID,
    segment: RoadSegment,
    prediction_horizon_days: int = 90,
    target_type: str = "DETERIORATION_RISK",
    persist: bool = True,
) -> DeteriorationPrediction:
    """Generate deterioration prediction for a road segment based on historical features.

    If sufficient historical data is missing (e.g. no completed inspections or health data),
    it generates an explicit INSUFFICIENT_DATA prediction rather than fabricating values.
    """
    model = await get_or_create_prediction_model(db)
    now = utc_now()

    # 1. Fetch latest completed inspection
    insp_query = (
        select(Inspection)
        .where(
            Inspection.organization_id == organization_id,
            # ANALYZED is the status the AI worker sets after processing.
            Inspection.status.in_(["SUBMITTED", "PROCESSING", "PROCESSED", "ANALYZED", "COMPLETED"]),
            (Inspection.road_segment_id == segment.id) | (Inspection.road_id == segment.road_id),
        )
        .order_by(desc(Inspection.captured_at))
        .limit(1)
    )
    latest_insp = (await db.execute(insp_query)).scalar_one_or_none()

    # 2. Fetch latest health snapshot
    health_query = (
        select(RoadHealthSnapshot)
        .where(
            RoadHealthSnapshot.organization_id == organization_id,
            RoadHealthSnapshot.road_segment_id == segment.id,
        )
        .order_by(desc(RoadHealthSnapshot.calculated_at))
        .limit(1)
    )
    latest_health = (await db.execute(health_query)).scalar_one_or_none()

    # 3. Check data sufficiency
    if latest_insp is None or latest_health is None or latest_health.health_score is None:
        prediction = DeteriorationPrediction(
            id=uuid.uuid4(),
            organization_id=organization_id,
            road_id=segment.road_id,
            road_segment_id=segment.id,
            model_id=model.id,
            prediction_horizon_days=prediction_horizon_days,
            target_type=target_type,
            predicted_value=None,
            predicted_risk=None,
            uncertainty_lower=None,
            uncertainty_upper=None,
            confidence=None,
            feature_version=FEATURE_VERSION,
            features={
                "reason": "Insufficient inspection and health snapshot history",
                "has_inspection": latest_insp is not None,
                "has_health_snapshot": latest_health is not None,
            },
            input_data_timestamp=now,
            generated_at=now,
            status="INSUFFICIENT_DATA",
            created_at=now,
        )
        if persist:
            db.add(prediction)
            await db.commit()
            await db.refresh(prediction)
        prediction.model = model
        return prediction

    # 4. Features (all from stored records; unknown values stay None)
    features = await extract_features(db, organization_id, segment, latest_health, latest_insp, now)
    features["prediction_horizon_days"] = prediction_horizon_days
    features["ml_training_readiness"] = await ml_training_readiness(db, organization_id)

    # 5. Rule-based estimate (hand-picked weights; not a trained regressor)
    estimate = rule_based_estimate(features, prediction_horizon_days)
    predicted_risk = estimate["risk"]
    predicted_value = estimate["projected_health"]
    features.update(
        risk_band=estimate["risk_band"],
        contributions=estimate["contributions"],
        projection_method=estimate["projection_method"],
        notes=estimate["notes"],
    )
    feature_dict = features

    # No confidence or uncertainty interval: a hand-weighted rule has no statistical
    # basis for one. These stay None until a trained model with evaluated error exists.
    uncertainty_lower = None
    uncertainty_upper = None
    confidence = None

    prediction = DeteriorationPrediction(
        id=uuid.uuid4(),
        organization_id=organization_id,
        road_id=segment.road_id,
        road_segment_id=segment.id,
        model_id=model.id,
        prediction_horizon_days=prediction_horizon_days,
        target_type=target_type,
        predicted_value=predicted_value,
        predicted_risk=predicted_risk,
        uncertainty_lower=uncertainty_lower,
        uncertainty_upper=uncertainty_upper,
        confidence=confidence,
        feature_version=FEATURE_VERSION,
        features=feature_dict,
        input_data_timestamp=now,
        generated_at=now,
        status="GENERATED",
        created_at=now,
    )

    if persist:
        db.add(prediction)
        await db.commit()
        await db.refresh(prediction)

    prediction.model = model
    return prediction


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def health_trend(points: list[tuple[datetime, float]]) -> tuple[float | None, int, int]:
    """Least-squares slope (health points per day) of scored snapshots; None unless at least
    two snapshots span TREND_MIN_SPAN_DAYS. Returns (slope, snapshot_count, span_days)."""
    if len(points) < 2:
        return None, len(points), 0
    t0 = points[0][0]
    xs = [(t - t0).total_seconds() / 86400.0 for t, _ in points]
    ys = [v for _, v in points]
    span = xs[-1] - xs[0]
    if span < TREND_MIN_SPAN_DAYS:
        return None, len(points), int(span)
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    den = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / den if den else 0.0
    return round(slope, 5), len(points), int(span)


async def extract_features(
    db: AsyncSession, organization_id: uuid.UUID, segment: RoadSegment, latest_health: RoadHealthSnapshot,
    latest_insp: Inspection, now: datetime,
) -> dict[str, Any]:
    from datetime import timedelta

    from app.models.maintenance import MaintenanceJob
    from app.models.road import Road
    from app.services.recurrence_engine import final_verification

    damages = list(
        (
            await db.execute(
                select(DamageRecord).where(
                    DamageRecord.organization_id == organization_id,
                    DamageRecord.road_segment_id == segment.id,
                    DamageRecord.status.in_(["DETECTED", "CONFIRMED", "MAINTENANCE_SCHEDULED", "IN_PROGRESS"]),
                )
            )
        ).scalars().all()
    )
    sev = {k: sum(1 for d in damages if str(d.severity).upper() == k) for k in ("CRITICAL", "HIGH", "MEDIUM", "LOW")}
    recs = (
        await db.execute(
            select(RecurrenceRecord.escalation_level).where(
                RecurrenceRecord.organization_id == organization_id,
                RecurrenceRecord.road_segment_id == segment.id,
                RecurrenceRecord.status.not_in(INACTIVE_RECURRENCE),
            )
        )
    ).scalars().all()
    if segment.length_meters is not None:
        length_m = float(segment.length_meters)
    elif segment.start_chainage is not None and segment.end_chainage is not None:
        length_m = float((segment.end_chainage - segment.start_chainage) * 1000)
    else:
        length_m = None

    snaps = (
        await db.execute(
            select(RoadHealthSnapshot.calculated_at, RoadHealthSnapshot.health_score)
            .where(
                RoadHealthSnapshot.organization_id == organization_id,
                RoadHealthSnapshot.road_segment_id == segment.id,
                RoadHealthSnapshot.health_score.is_not(None),
                RoadHealthSnapshot.calculated_at >= now - timedelta(days=TREND_WINDOW_DAYS),
            )
            .order_by(RoadHealthSnapshot.calculated_at)
        )
    ).all()
    slope, n_snaps, span = health_trend([(_utc(t), float(v)) for t, v in snaps])

    inspections_365 = (
        await db.execute(
            select(func.count(Inspection.id)).where(
                Inspection.organization_id == organization_id,
                (Inspection.road_segment_id == segment.id) | (Inspection.road_id == segment.road_id),
                Inspection.captured_at >= now - timedelta(days=365),
            )
        )
    ).scalar() or 0
    last_repair = (
        await db.execute(
            select(MaintenanceJob)
            .where(
                MaintenanceJob.organization_id == organization_id,
                MaintenanceJob.road_segment_id == segment.id,
                MaintenanceJob.completed_at.is_not(None),
            )
            .order_by(desc(MaintenanceJob.completed_at))
            .limit(1)
        )
    ).scalar_one_or_none()
    last_result = None
    if last_repair is not None:
        _, last_result, _ = await final_verification(db, last_repair.id)
    road = await db.get(Road, segment.road_id) if segment.road_id else None
    insp_at = _utc(latest_insp.captured_at)
    return {
        "length_meters": length_m,
        "total_damages": len(damages),
        "critical_damage_count": sev["CRITICAL"],
        "high_damage_count": sev["HIGH"],
        "medium_damage_count": sev["MEDIUM"],
        "low_damage_count": sev["LOW"],
        "damage_density_per_km": round(len(damages) / (length_m / 1000.0), 3) if length_m else None,
        "repeat_observations": sum(max(0, (d.observation_count or 1) - 1) for d in damages),
        "recurrence_count": len(recs),
        "escalated_recurrence_count": sum(1 for lvl in recs if lvl in ("ELEVATED", "CRITICAL")),
        "current_health_score": float(latest_health.health_score),
        "health_trend_points_per_day": slope,
        "health_trend_snapshot_count": n_snaps,
        "health_trend_span_days": span,
        "days_since_last_inspection": (now - insp_at).days if insp_at else None,
        "inspections_last_365_days": inspections_365,
        "days_since_last_repair": (now - _utc(last_repair.completed_at)).days if last_repair else None,
        "last_repair_verification_result": last_result,
        "traffic_volume_class": road.traffic_volume_class if road else None,
    }


TRAFFIC_POINTS = {"LOW": 0.0, "MEDIUM": 1.5, "HIGH": 3.0, "VERY_HIGH": 5.0}


def rule_based_estimate(f: dict[str, Any], horizon_days: int) -> dict[str, Any]:
    """Hand-weighted risk score (0-100) with every contribution itemised."""
    notes: list[str] = []
    c: dict[str, float] = {}
    c["damage_severity"] = min(
        50.0,
        f["critical_damage_count"] * 20 + f["high_damage_count"] * 12 + f["medium_damage_count"] * 5
        + f["low_damage_count"] * 1.5,
    )
    c["health_deficit"] = round(min(30.0, (100.0 - f["current_health_score"]) * 0.3), 2)
    slope = f["health_trend_points_per_day"]
    if slope is None:
        c["health_trend"] = 0.0
        notes.append("No observed health trend yet (needs scored snapshots spanning at least "
                     f"{TREND_MIN_SPAN_DAYS} days); trend not included.")
    else:
        c["health_trend"] = round(min(15.0, max(0.0, -slope * horizon_days * 0.5)), 2)
    c["recurrence"] = min(18.0, f["recurrence_count"] * 6.0) + min(8.0, f["escalated_recurrence_count"] * 4.0)
    c["repair_quality"] = {"SUBSTANDARD": 8.0, "UNRESOLVED": 4.0}.get(f["last_repair_verification_result"] or "", 0.0)
    days = f["days_since_last_inspection"]
    c["inspection_staleness"] = round(min(8.0, days / 45.0), 2) if days is not None else 0.0
    traffic = f["traffic_volume_class"]
    c["traffic"] = TRAFFIC_POINTS.get(traffic, 0.0) if traffic else 0.0
    if not traffic:
        notes.append("Traffic volume unknown (no documented source); not included.")
    horizon_factor = 1.0 + 0.25 * horizon_days / 365.0
    risk = round(min(100.0, max(0.0, sum(c.values()) * horizon_factor)), 2)
    band = "SEVERE" if risk >= 75 else "HIGH" if risk >= 50 else "MODERATE" if risk >= 25 else "LOW"
    projected = None
    method = None
    if slope is not None:
        projected = round(min(100.0, max(0.0, f["current_health_score"] + slope * horizon_days)), 2)
        method = "LINEAR_TREND_EXTRAPOLATION"
    else:
        notes.append("No future health value: it would require an observed trend.")
    return {
        "risk": risk,
        "risk_band": band,
        "contributions": {**c, "horizon_factor": round(horizon_factor, 4)},
        "projected_health": projected,
        "projection_method": method,
        "notes": notes,
    }


async def ml_training_readiness(db: AsyncSession, organization_id: uuid.UUID) -> dict[str, Any]:
    """How much outcome history exists for training a regressor (counted, not assumed)."""
    rows = (
        await db.execute(
            select(
                RoadHealthSnapshot.road_segment_id,
                func.count(RoadHealthSnapshot.id),
                func.min(RoadHealthSnapshot.calculated_at),
                func.max(RoadHealthSnapshot.calculated_at),
            )
            .where(
                RoadHealthSnapshot.organization_id == organization_id,
                RoadHealthSnapshot.road_segment_id.is_not(None),
                RoadHealthSnapshot.health_score.is_not(None),
            )
            .group_by(RoadHealthSnapshot.road_segment_id)
        )
    ).all()
    usable = sum(
        1 for _, n, lo, hi in rows
        if n >= 2 and lo is not None and hi is not None and (_utc(hi) - _utc(lo)).days >= ML_MIN_SPAN_DAYS
    )
    return {
        "segments_with_outcome_history": usable,
        "required_segments": ML_MIN_TRAINING_SEGMENTS,
        "required_span_days": ML_MIN_SPAN_DAYS,
        "status": "READY_FOR_TRAINING" if usable >= ML_MIN_TRAINING_SEGMENTS else "INSUFFICIENT_DATA",
        "model_trained": False,
    }
