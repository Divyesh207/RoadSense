import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import OrgContext, require_permission
from app.core.database import get_db
from app.models.intelligence import DeteriorationPrediction
from app.models.road import RoadSegment
from app.schemas.common import (
    PaginatedResponseEnvelope,
    PaginationMeta,
    ResponseEnvelope,
    ResponseMeta,
)
from app.schemas.prediction import (
    PredictionRequest,
    PredictionResponseData,
)
from app.services.prediction_engine import (
    ESTIMATION_METHOD,
    MODEL_FAMILY,
    MODEL_NAME,
    MODEL_VERSION,
    RULE_BASED_DISCLAIMER,
    predict_segment_deterioration,
)
from app.services.road_lifecycle import refresh_segment_job_priorities

router = APIRouter()


from sqlalchemy import inspect as sa_inspect


def get_loaded_rel(instance: Any, attr_name: str, default: Any = None) -> Any:
    try:
        state = sa_inspect(instance)
        if attr_name in state.dict:
            return getattr(instance, attr_name)
    except (AttributeError, KeyError, TypeError):
        return default
    return default


def build_prediction_response(prediction: DeteriorationPrediction) -> PredictionResponseData:
    model = get_loaded_rel(prediction, "model")
    model_name = model.name if model else MODEL_NAME
    model_version = model.version if model else MODEL_VERSION
    rule_based = (model.model_family == MODEL_FAMILY) if model else True


    return PredictionResponseData(
        id=prediction.id,
        organization_id=prediction.organization_id,
        road_id=prediction.road_id,
        road_segment_id=prediction.road_segment_id,
        model_id=prediction.model_id,
        model_name=model_name,
        model_version=model_version,
        prediction_horizon_days=prediction.prediction_horizon_days,
        target_type=prediction.target_type,
        predicted_risk=float(prediction.predicted_risk) if prediction.predicted_risk is not None else None,
        predicted_value=float(prediction.predicted_value) if prediction.predicted_value is not None else None,
        uncertainty_lower=float(prediction.uncertainty_lower) if prediction.uncertainty_lower is not None else None,
        uncertainty_upper=float(prediction.uncertainty_upper) if prediction.uncertainty_upper is not None else None,
        confidence=float(prediction.confidence) if prediction.confidence is not None else None,
        feature_version=prediction.feature_version,
        features=prediction.features or {},
        input_data_timestamp=prediction.input_data_timestamp,
        generated_at=prediction.generated_at,
        status=prediction.status,
        estimation_method=ESTIMATION_METHOD if rule_based else "TRAINED_MODEL",
        **({"disclaimer": RULE_BASED_DISCLAIMER} if rule_based else {}),
    )


@router.get(
    "/{segment_id}/predictions",
    response_model=ResponseEnvelope[PredictionResponseData],
    summary="Get latest deterioration prediction for a road segment",
)
async def get_segment_prediction(
    segment_id: uuid.UUID,
    request: Request,
    org_context: Annotated[OrgContext, Depends(require_permission("predictions:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    segment = await db.get(RoadSegment, segment_id)
    if not segment or segment.organization_id != org_context.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SEGMENT_NOT_FOUND", "message": "Road segment was not found."},
        )

    q = (
        select(DeteriorationPrediction)
        .options(selectinload(DeteriorationPrediction.model))
        .where(
            DeteriorationPrediction.organization_id == org_context.organization_id,
            DeteriorationPrediction.road_segment_id == segment.id,
        )
        .order_by(desc(DeteriorationPrediction.generated_at))
        .limit(1)
    )
    prediction = (await db.execute(q)).scalar_one_or_none()

    if prediction is None:
        prediction = await predict_segment_deterioration(
            db=db,
            organization_id=org_context.organization_id,
            segment=segment,
            prediction_horizon_days=90,
            persist=True,
        )

    return ResponseEnvelope(
        data=build_prediction_response(prediction),
        meta=ResponseMeta(request_id=getattr(request.state, "request_id", None)),
    )


@router.post(
    "/{segment_id}/predictions",
    response_model=ResponseEnvelope[PredictionResponseData],
    summary="Request a new deterioration prediction for a road segment",
)
async def create_segment_prediction(
    segment_id: uuid.UUID,
    request: Request,
    org_context: Annotated[OrgContext, Depends(require_permission("predictions:create"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    payload: PredictionRequest | None = None,
):
    segment = await db.get(RoadSegment, segment_id)
    if not segment or segment.organization_id != org_context.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SEGMENT_NOT_FOUND", "message": "Road segment was not found."},
        )

    horizon = payload.prediction_horizon_days if payload else 90
    target_type = payload.target_type if payload else "DETERIORATION_RISK"
    persist = payload.persist if payload else True

    prediction = await predict_segment_deterioration(
        db=db,
        organization_id=org_context.organization_id,
        segment=segment,
        prediction_horizon_days=horizon,
        target_type=target_type,
        persist=persist,
    )
    if persist and prediction.status == "GENERATED":
        # The estimate is a priority input for open AUTO jobs on this segment.
        await refresh_segment_job_priorities(db, org_context.organization_id, segment.id)

    return ResponseEnvelope(
        data=build_prediction_response(prediction),
        meta=ResponseMeta(request_id=getattr(request.state, "request_id", None)),
    )


@router.get(
    "/{segment_id}/predictions/history",
    response_model=PaginatedResponseEnvelope[PredictionResponseData],
    summary="Get chronological history of deterioration predictions for a road segment",
)
async def get_segment_prediction_history(
    segment_id: uuid.UUID,
    request: Request,
    org_context: Annotated[OrgContext, Depends(require_permission("predictions:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    segment = await db.get(RoadSegment, segment_id)
    if not segment or segment.organization_id != org_context.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SEGMENT_NOT_FOUND", "message": "Road segment was not found."},
        )

    count_q = select(func.count(DeteriorationPrediction.id)).where(
        DeteriorationPrediction.organization_id == org_context.organization_id,
        DeteriorationPrediction.road_segment_id == segment.id,
    )
    total_count = (await db.execute(count_q)).scalar() or 0
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0

    history_q = (
        select(DeteriorationPrediction)
        .options(selectinload(DeteriorationPrediction.model))
        .where(
            DeteriorationPrediction.organization_id == org_context.organization_id,
            DeteriorationPrediction.road_segment_id == segment.id,
        )
        .order_by(desc(DeteriorationPrediction.generated_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    predictions = (await db.execute(history_q)).scalars().all()

    items = [build_prediction_response(p) for p in predictions]

    return PaginatedResponseEnvelope(
        data=items,
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
            request_id=getattr(request.state, "request_id", None),
        ),
    )
