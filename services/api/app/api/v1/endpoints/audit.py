import math
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import OrgContext, require_role
from app.core.database import get_db
from app.schemas.audit import AuditLogFilter, AuditLogItem
from app.schemas.common import PaginatedResponseEnvelope, PaginationMeta
from app.services.audit_service import AuditService

router = APIRouter()


@router.get("", response_model=PaginatedResponseEnvelope[AuditLogItem])
async def list_audit_logs(
    org_context: Annotated[OrgContext, Depends(require_role(["ADMINISTRATOR", "ROAD_AUTHORITY"]))],
    db: Annotated[AsyncSession, Depends(get_db)],
    action: str | None = Query(None, description="Filter by action name"),
    entity_type: str | None = Query(None, description="Filter by entity type"),
    entity_id: uuid.UUID | None = Query(None, description="Filter by entity ID"),
    actor_user_id: uuid.UUID | None = Query(None, description="Filter by actor user ID"),
    from_date: datetime | None = Query(None, description="Filter from timestamp"),
    to_date: datetime | None = Query(None, description="Filter to timestamp"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
):
    """
    List security and operational audit logs for the current organization.
    Restricted to Administrators and Road Authorities.
    """
    filters = AuditLogFilter(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        actor_user_id=actor_user_id,
        from_date=from_date,
        to_date=to_date,
    )

    items, total_count = await AuditService.list_audit_logs(
        db=db,
        organization_id=org_context.organization_id,
        filters=filters,
        page=page,
        page_size=page_size,
    )

    total_pages = math.ceil(total_count / page_size) if total_count > 0 else 0

    return PaginatedResponseEnvelope(
        success=True,
        data=items,
        meta=PaginationMeta(
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    )
