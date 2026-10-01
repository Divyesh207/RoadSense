import math
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import OrgContext, require_permission
from app.core.database import get_db
from app.schemas.common import (
    PaginatedResponseEnvelope,
    PaginationMeta,
    ResponseEnvelope,
    ResponseMeta,
)
from app.schemas.report import (
    ReportCreateRequest,
    ReportCreateResponseData,
    ReportDownloadUrlResponseData,
    ReportResponseData,
)
from app.services.report_service import ReportService

router = APIRouter()


@router.post(
    "",
    response_model=ResponseEnvelope[ReportCreateResponseData],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request generation of an operational report (asynchronous)",
)
async def create_report(
    payload: ReportCreateRequest,
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("reports:create"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[ReportCreateResponseData]:
    data = await ReportService.create_report(
        db=db,
        org_id=org_ctx.organization_id,
        user_id=org_ctx.user_id,
        payload=payload,
    )
    return ResponseEnvelope(
        success=True,
        data=data,
        meta=ResponseMeta(request_id=getattr(request.state, "request_id", None)),
    )


@router.get(
    "",
    response_model=PaginatedResponseEnvelope[ReportResponseData],
    summary="List generated reports for organization with pagination",
)
async def list_reports(
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("reports:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    report_status: str | None = Query(None, alias="status"),
    report_type: str | None = Query(None, alias="type"),
) -> PaginatedResponseEnvelope[ReportResponseData]:
    items, total = await ReportService.list_reports(
        db=db,
        org_id=org_ctx.organization_id,
        page=page,
        page_size=page_size,
        status=report_status,
        report_type=report_type,
    )
    total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1

    return PaginatedResponseEnvelope(
        success=True,
        data=items,
        meta=PaginationMeta(
            request_id=getattr(request.state, "request_id", None),
            page=page,
            page_size=page_size,
            total_count=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    )


@router.get(
    "/{report_id}",
    response_model=ResponseEnvelope[ReportResponseData],
    summary="Get report metadata and processing status",
)
async def get_report(
    report_id: uuid.UUID,
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("reports:read"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[ReportResponseData]:
    data = await ReportService.get_report_by_id(
        db=db,
        org_id=org_ctx.organization_id,
        report_id=report_id,
    )
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Report not found."},
        )

    return ResponseEnvelope(
        success=True,
        data=data,
        meta=ResponseMeta(request_id=getattr(request.state, "request_id", None)),
    )


@router.get(
    "/{report_id}/download-url",
    response_model=ResponseEnvelope[ReportDownloadUrlResponseData],
    summary="Generate secure short-lived download URL for report",
)
async def get_report_download_url(
    report_id: uuid.UUID,
    request: Request,
    org_ctx: Annotated[OrgContext, Depends(require_permission("reports:download"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ResponseEnvelope[ReportDownloadUrlResponseData]:
    data = await ReportService.generate_download_url(
        db=db,
        org_id=org_ctx.organization_id,
        report_id=report_id,
    )
    if not data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Report not found."},
        )

    return ResponseEnvelope(
        success=True,
        data=data,
        meta=ResponseMeta(request_id=getattr(request.state, "request_id", None)),
    )
