import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.history import GeneratedReport
from app.schemas.report import (
    ReportCreateRequest,
    ReportCreateResponseData,
    ReportDownloadUrlResponseData,
    ReportResponseData,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ReportService:

    @staticmethod
    async def create_report(
        db: AsyncSession,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: ReportCreateRequest,
    ) -> ReportCreateResponseData:
        report_id = uuid.uuid4()
        now = utc_now()

        # Simulated report artifact path
        ext = payload.parameters.get("format", "JSON").lower()
        storage_path = f"reports/{org_id}/{report_id}.{ext}"

        report = GeneratedReport(
            id=report_id,
            organization_id=org_id,
            requested_by_user_id=user_id,
            report_type=payload.report_type.upper(),
            status="COMPLETED",  # Immediately generated for operational intelligence
            parameters=payload.parameters,
            storage_bucket="reports",
            storage_path=storage_path,
            generated_at=now,
            expires_at=now + timedelta(days=7),
            created_at=now,
            updated_at=now,
        )
        db.add(report)
        await db.commit()
        await db.refresh(report)

        return ReportCreateResponseData(
            report_id=report.id,
            status=report.status,
            report_type=report.report_type,
            created_at=report.created_at,
        )

    @staticmethod
    async def list_reports(
        db: AsyncSession,
        org_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
        status: str | None = None,
        report_type: str | None = None,
    ) -> tuple[list[ReportResponseData], int]:
        stmt = select(GeneratedReport).where(GeneratedReport.organization_id == org_id)

        if status:
            stmt = stmt.where(GeneratedReport.status == status.upper())
        if report_type:
            stmt = stmt.where(GeneratedReport.report_type == report_type.upper())

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt)).scalar() or 0

        offset = (page - 1) * page_size
        stmt = stmt.order_by(GeneratedReport.created_at.desc()).offset(offset).limit(page_size)
        results = (await db.execute(stmt)).scalars().all()

        data = [
            ReportResponseData(
                id=r.id,
                organization_id=r.organization_id,
                requested_by_user_id=r.requested_by_user_id,
                report_type=r.report_type,
                status=r.status,
                parameters=r.parameters or {},
                storage_path=r.storage_path,
                generated_at=r.generated_at,
                expires_at=r.expires_at,
                error_message=r.error_message,
                created_at=r.created_at,
            )
            for r in results
        ]

        return data, total

    @staticmethod
    async def get_report_by_id(
        db: AsyncSession,
        org_id: uuid.UUID,
        report_id: uuid.UUID,
    ) -> ReportResponseData | None:
        stmt = select(GeneratedReport).where(
            GeneratedReport.id == report_id,
            GeneratedReport.organization_id == org_id,
        )
        r = (await db.execute(stmt)).scalar_one_or_none()
        if not r:
            return None

        return ReportResponseData(
            id=r.id,
            organization_id=r.organization_id,
            requested_by_user_id=r.requested_by_user_id,
            report_type=r.report_type,
            status=r.status,
            parameters=r.parameters or {},
            storage_path=r.storage_path,
            generated_at=r.generated_at,
            expires_at=r.expires_at,
            error_message=r.error_message,
            created_at=r.created_at,
        )

    @staticmethod
    async def generate_download_url(
        db: AsyncSession,
        org_id: uuid.UUID,
        report_id: uuid.UUID,
    ) -> ReportDownloadUrlResponseData | None:
        report = await ReportService.get_report_by_id(db, org_id, report_id)
        if not report:
            return None

        expires_in = 3600  # 1 hour
        download_url = f"https://storage.roadsense.internal/reports/{org_id}/{report_id}?token=mock_signed_{report_id}"

        return ReportDownloadUrlResponseData(
            report_id=report.id,
            download_url=download_url,
            expires_in_seconds=expires_in,
        )
