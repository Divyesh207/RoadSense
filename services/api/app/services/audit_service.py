import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.history import AuditLog
from app.schemas.audit import AuditLogFilter


class AuditService:
    @staticmethod
    async def record_audit_event(
        db: AsyncSession,
        action: str,
        entity_type: str,
        entity_id: uuid.UUID | None = None,
        actor_user_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
        request_id: str | None = None,
        before_data: dict[str, Any] | None = None,
        after_data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        """
        Record a secure audit log entry for sensitive domain events.
        """
        audit_entry = AuditLog(
            id=uuid.uuid4(),
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            request_id=request_id,
            before_data=before_data,
            after_data=after_data,
            metadata_=metadata,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db.add(audit_entry)
        await db.flush()
        return audit_entry

    @staticmethod
    async def list_audit_logs(
        db: AsyncSession,
        organization_id: uuid.UUID,
        filters: AuditLogFilter,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AuditLog], int]:
        """
        Query audit logs strictly scoped to the active organization.
        """
        stmt = select(AuditLog).where(AuditLog.organization_id == organization_id)

        if filters.action:
            stmt = stmt.where(AuditLog.action == filters.action)
        if filters.entity_type:
            stmt = stmt.where(AuditLog.entity_type == filters.entity_type)
        if filters.entity_id:
            stmt = stmt.where(AuditLog.entity_id == filters.entity_id)
        if filters.actor_user_id:
            stmt = stmt.where(AuditLog.actor_user_id == filters.actor_user_id)
        if filters.from_date:
            stmt = stmt.where(AuditLog.created_at >= filters.from_date)
        if filters.to_date:
            stmt = stmt.where(AuditLog.created_at <= filters.to_date)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(count_stmt)
        total_count = total_result.scalar_one()

        # Paginate
        offset = (page - 1) * page_size
        stmt = stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(page_size)

        result = await db.execute(stmt)
        entries = list(result.scalars().all())

        return entries, total_count
