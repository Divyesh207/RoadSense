import uuid
from datetime import datetime, timezone
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
MODEL_VERSION = "rules-v1"
MODEL_FAMILY = "RULE_BASED"
ESTIMATION_METHOD = "RULE_BASED_ESTIMATE"
FEATURE_VERSION = "feat-v1.0.0"
RULE_BASED_DISCLAIMER = (
    "Rule-based deterioration estimate from hand-weighted factors (damage severity counts, "
    "recurrence, current health, inspection age). It is not a trained or validated model, has no "
    "statistical confidence, and must not be treated as a guaranteed future outcome."
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


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
                "description": "Hand-weighted rules over damage severity counts, recurrence, current "
                "health and inspection age. Not a trained or evaluated model.",
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

    # 4. Feature Extraction
    damages_query = select(DamageRecord).where(
        DamageRecord.organization_id == organization_id,
        DamageRecord.road_segment_id == segment.id,
        DamageRecord.status.in_(["DETECTED", "CONFIRMED", "MAINTENANCE_SCHEDULED", "IN_PROGRESS"]),
    )
    damages = list((await db.execute(damages_query)).scalars().all())

    recurrence_query = select(func.count(RecurrenceRecord.id)).where(
        RecurrenceRecord.organization_id == organization_id,
        RecurrenceRecord.road_segment_id == segment.id,
    )
    recurrence_count = (await db.execute(recurrence_query)).scalar() or 0

    crit_count = sum(1 for d in damages if str(d.severity).upper() == "CRITICAL")
    high_count = sum(1 for d in damages if str(d.severity).upper() == "HIGH")
    med_count = sum(1 for d in damages if str(d.severity).upper() == "MEDIUM")
    low_count = sum(1 for d in damages if str(d.severity).upper() == "LOW")

    length_m = (
        float(segment.length_meters)
        if segment.length_meters is not None
        else (
            float((segment.end_chainage - segment.start_chainage) * 1000)
            if segment.start_chainage is not None and segment.end_chainage is not None
            else 100.0
        )
    )
    length_km = max(0.05, length_m / 1000.0)
    damage_density = round(len(damages) / length_km, 3)

    current_health = float(latest_health.health_score)
    days_since_inspection = (
        (now - latest_insp.captured_at).days if latest_insp.captured_at else 0
    )

    feature_dict: dict[str, Any] = {
        "length_meters": length_m,
        "total_damages": len(damages),
        "critical_damage_count": crit_count,
        "high_damage_count": high_count,
        "medium_damage_count": med_count,
        "low_damage_count": low_count,
        "damage_density_per_km": damage_density,
        "recurrence_count": recurrence_count,
        "current_health_score": current_health,
        "days_since_last_inspection": days_since_inspection,
        "prediction_horizon_days": prediction_horizon_days,
    }

    # 5. Rule-based estimate (hand-picked weights; not a trained regressor)
    time_factor = prediction_horizon_days / 365.0
    damage_severity_weight = (
        crit_count * 28.0 + high_count * 16.0 + med_count * 7.0 + low_count * 2.0
    )
    recurrence_weight = recurrence_count * 10.0
    health_deficit = (100.0 - current_health) * 0.45
    inspection_age_factor = min(15.0, days_since_inspection * 0.05)

    base_risk = (
        (damage_severity_weight + recurrence_weight + health_deficit + inspection_age_factor)
        * (1.0 + 0.35 * time_factor)
    )
    predicted_risk = round(min(100.0, max(0.0, base_risk)), 2)

    health_drop = round(
        min(
            current_health,
            (predicted_risk * 0.32 * (prediction_horizon_days / 180.0)) + (8.0 * time_factor),
        ),
        2,
    )
    predicted_value = round(max(0.0, current_health - health_drop), 2)

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
