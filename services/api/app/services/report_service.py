import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlencode

from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.history import GeneratedReport
from app.schemas.report import (
    ReportCreateRequest,
    ReportCreateResponseData,
    ReportDownloadUrlResponseData,
    ReportResponseData,
)
from app.services.report_render import RENDERERS, SUPPORTED_FORMATS
from app.services.storage import (
    StorageError,
    get_storage_backend,
    storage_http_exception,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


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
        report_type = payload.report_type.upper()
        requested_format = str(payload.parameters.get("format", "JSON")).upper()
        if requested_format not in SUPPORTED_FORMATS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "UNSUPPORTED_REPORT_FORMAT",
                    "message": f"Report format must be one of {', '.join(SUPPORTED_FORMATS)}.",
                },
            )

        # One snapshot of live analytics, rendered in the requested format (JSON, CSV or PDF).
        content = await ReportService._build_report_content(db, org_id, report_type, payload.parameters, now)
        if requested_format == "PDF" and report_type == "ROAD_HEALTH":
            # The designed PDF needs per-segment and per-defect records; JSON and CSV keep their shape.
            from app.services.road_health_report import build_road_health_detail

            content["road_health_detail"] = await build_road_health_detail(db, org_id, payload.parameters, now, report_id)
        extension, content_type = SUPPORTED_FORMATS[requested_format]
        filename = f"{report_type.lower()}_report_{now:%Y%m%d_%H%M%S}.{extension}"
        bucket = settings.SUPABASE_STORAGE_BUCKET_REPORTS
        storage_path = f"reports/{org_id}/{report_id}.{extension}"
        parameters = {
            **payload.parameters,
            "requested_format": requested_format,
            "artifact_format": requested_format,
            "artifact_filename": filename,
            "artifact_content_type": content_type,
        }

        status_value, error_message, generated_at = "COMPLETED", None, now
        try:
            body = await run_in_threadpool(RENDERERS[requested_format], content)
            await run_in_threadpool(
                lambda: get_storage_backend().put_object(bucket, storage_path, body, content_type)
            )
        except StorageError as exc:
            status_value, error_message, generated_at = "FAILED", f"Report artifact upload failed: {exc}", None

        report = GeneratedReport(
            id=report_id,
            organization_id=org_id,
            requested_by_user_id=user_id,
            report_type=report_type,
            status=status_value,
            parameters=parameters,
            storage_bucket=bucket,
            storage_path=storage_path if status_value == "COMPLETED" else None,
            generated_at=generated_at,
            expires_at=now + timedelta(days=7),
            error_message=error_message,
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
    async def _build_report_content(
        db: AsyncSession,
        org_id: uuid.UUID,
        report_type: str,
        parameters: dict[str, Any],
        generated_at: datetime,
    ) -> dict[str, Any]:
        from app.services.analytics_service import AnalyticsService

        sections: dict[str, Any] = {}
        if report_type in ("ROAD_HEALTH", "EXECUTIVE_ROAD_CONDITION"):
            sections["road_health"] = await AnalyticsService.get_road_health_analytics(db, org_id)
        if report_type in ("DAMAGE_SUMMARY", "EXECUTIVE_ROAD_CONDITION"):
            sections["damage_trends"] = await AnalyticsService.get_damage_trends(db, org_id)
        if report_type in ("MAINTENANCE_LOG", "EXECUTIVE_ROAD_CONDITION"):
            sections["maintenance"] = await AnalyticsService.get_maintenance_analytics(db, org_id)
        if report_type in ("INSPECTION_SUMMARY", "EXECUTIVE_ROAD_CONDITION"):
            sections["inspections"] = await AnalyticsService.get_inspection_analytics(db, org_id)
        if not sections:
            sections["dashboard_summary"] = await AnalyticsService.get_dashboard_summary(db, org_id)

        return {
            "report_type": report_type,
            "organization_id": str(org_id),
            "generated_at": generated_at.isoformat(),
            "parameters": parameters,
            "sections": {k: v.model_dump(mode="json") for k, v in sections.items()},
        }

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

        if report.status != "COMPLETED" or not report.storage_path:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "REPORT_ARTIFACT_NOT_AVAILABLE",
                    "message": f"Report is {report.status}; no artifact is available for download.",
                },
            )
        expires_in = settings.SIGNED_DOWNLOAD_EXPIRES_SECONDS
        bucket = settings.SUPABASE_STORAGE_BUCKET_REPORTS
        try:
            download_url = await run_in_threadpool(
                lambda: get_storage_backend().create_signed_download_url(bucket, report.storage_path, expires_in)
            )
        except StorageError as exc:
            raise storage_http_exception(exc) from exc

        # Ask storage to serve the object as an attachment with its real file name
        # (Supabase and the local backend both honour the `download` query parameter).
        filename = (report.parameters or {}).get("artifact_filename") or report.storage_path.rsplit("/", 1)[-1]
        separator = "&" if "?" in download_url else "?"
        download_url = f"{download_url}{separator}{urlencode({'download': filename})}"

        return ReportDownloadUrlResponseData(
            report_id=report.id,
            download_url=download_url,
            expires_in_seconds=expires_in,
        )
