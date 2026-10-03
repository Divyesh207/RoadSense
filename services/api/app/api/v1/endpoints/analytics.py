import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import OrgContext, require_permission
from app.core.database import get_db
from app.schemas.analytics import (
    DamageTrendsData,
    DashboardSummaryData,
    InspectionAnalyticsData,
    MaintenanceAnalyticsData,
    RoadHealthAnalyticsData,
)
from app.schemas.common import ResponseEnvelope, ResponseMeta
from app.services.analytics_service import AnalyticsService
from app.services.road_intelligence import (
    contractor_history,
    priority_overview,
    recurrence_overview,
    verification_overview,
)

router = APIRouter()
dashboard_router = APIRouter()


@dashboard_router.get(
    "/summary",
    response_model=ResponseEnvelope[DashboardSummaryData],
    summary="Get overall organization dashboard operational summary metrics",
)
async def get_dashboard_summary(
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("roads:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[DashboardSummaryData]:
    data = await AnalyticsService.get_dashboard_summary(db, org_ctx.organization_id)
    return ResponseEnvelope(
        success=True,
        data=data,
        meta=ResponseMeta(request_id=getattr(request.state, "request_id", None)),
    )


@router.get(
    "/damage-trends",
    response_model=ResponseEnvelope[DamageTrendsData],
    summary="Get temporal and category-wise damage trends",
)
async def get_damage_trends(
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("roads:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_date: datetime | None = Query(None, alias="from"),
    to_date: datetime | None = Query(None, alias="to"),
    road_id: uuid.UUID | None = Query(None),
    damage_type: str | None = Query(None),
    severity: str | None = Query(None),
) -> ResponseEnvelope[DamageTrendsData]:
    data = await AnalyticsService.get_damage_trends(
        db=db,
        org_id=org_ctx.organization_id,
        from_date=from_date,
        to_date=to_date,
        road_id=road_id,
        damage_type=damage_type,
        severity=severity,
    )
    return ResponseEnvelope(
        success=True,
        data=data,
        meta=ResponseMeta(request_id=getattr(request.state, "request_id", None)),
    )


@router.get(
    "/road-health",
    response_model=ResponseEnvelope[RoadHealthAnalyticsData],
    summary="Get road health distribution and critical segments analytics",
)
async def get_road_health_analytics(
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("roads:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[RoadHealthAnalyticsData]:
    data = await AnalyticsService.get_road_health_analytics(db, org_ctx.organization_id)
    return ResponseEnvelope(
        success=True,
        data=data,
        meta=ResponseMeta(request_id=getattr(request.state, "request_id", None)),
    )


@router.get(
    "/maintenance",
    response_model=ResponseEnvelope[MaintenanceAnalyticsData],
    summary="Get maintenance verification rates, completion times, and repair performance",
)
async def get_maintenance_analytics(
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("roads:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[MaintenanceAnalyticsData]:
    data = await AnalyticsService.get_maintenance_analytics(db, org_ctx.organization_id)
    return ResponseEnvelope(
        success=True,
        data=data,
        meta=ResponseMeta(request_id=getattr(request.state, "request_id", None)),
    )


@router.get(
    "/inspections",
    response_model=ResponseEnvelope[InspectionAnalyticsData],
    summary="Get inspection and AI pipeline throughput analytics",
)
async def get_inspection_analytics(
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("roads:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[InspectionAnalyticsData]:
    data = await AnalyticsService.get_inspection_analytics(db, org_ctx.organization_id)
    return ResponseEnvelope(
        success=True,
        data=data,
        meta=ResponseMeta(request_id=getattr(request.state, "request_id", None)),
    )


@router.get(
    "/contractors",
    response_model=ResponseEnvelope[list[dict[str, Any]]],
    summary="Assignee (user / contractor organization) history: jobs, verification outcomes, recurrences after repair",
)
async def get_contractor_history(
    org_ctx: Annotated[OrgContext, Depends(require_permission("maintenance:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return ResponseEnvelope(data=await contractor_history(db, org_ctx.organization_id))


@router.get(
    "/repair-verifications",
    response_model=ResponseEnvelope[list[dict[str, Any]]],
    summary="Automated repair image analyses with their latest human review",
)
async def get_repair_verification_overview(
    org_ctx: Annotated[OrgContext, Depends(require_permission("maintenance:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
):
    return ResponseEnvelope(data=await verification_overview(db, org_ctx.organization_id, limit))


@router.get(
    "/recurrences",
    response_model=ResponseEnvelope[list[dict[str, Any]]],
    summary="Recurring damage locations with previous repair, verification result and escalation",
)
async def get_recurrence_overview(
    org_ctx: Annotated[OrgContext, Depends(require_permission("roads:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
):
    return ResponseEnvelope(data=await recurrence_overview(db, org_ctx.organization_id, limit))


@router.get(
    "/priorities",
    response_model=ResponseEnvelope[list[dict[str, Any]]],
    summary="Open maintenance jobs ranked by priority with the factors behind each score",
)
async def get_priority_overview(
    org_ctx: Annotated[OrgContext, Depends(require_permission("maintenance:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return ResponseEnvelope(data=await priority_overview(db, org_ctx.organization_id))
