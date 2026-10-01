from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, status
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.database import check_db_health
from app.schemas.common import ResponseEnvelope

router = APIRouter()


@router.get("/live", response_model=ResponseEnvelope[dict[str, Any]])
async def health_live() -> ResponseEnvelope[dict[str, Any]]:
    return ResponseEnvelope(
        success=True,
        data={
            "status": "alive",
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.APP_ENV,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )


@router.get("/ready", response_model=ResponseEnvelope[dict[str, Any]])
async def health_ready():
    db_ok = await check_db_health()

    checks = {
        "database": "connected" if db_ok else "disconnected",
    }

    all_ready = db_ok

    content = ResponseEnvelope(
        success=all_ready,
        data={
            "status": "ready" if all_ready else "not_ready",
            "checks": checks,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        error=None if all_ready else {
            "code": "DEPENDENCY_UNAVAILABLE",
            "message": "One or more critical services are not ready",
            "details": checks,
        },
    )

    if not all_ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=content.model_dump(mode="json"),
        )

    return content
