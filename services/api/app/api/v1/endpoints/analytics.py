import uuid
from datetime import datetime
from typing import Annotated

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
