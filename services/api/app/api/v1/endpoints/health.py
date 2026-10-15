from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from redis.asyncio import from_url as async_redis_from_url
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.database import get_db
from app.schemas.common import ResponseEnvelope
from app.services.storage import StorageError, get_storage_backend

router = APIRouter()


async def check_redis_health() -> tuple[bool, str]:
    if not settings.REDIS_URL:
        return True, "not_configured"
    try:
        client = async_redis_from_url(settings.REDIS_URL, socket_connect_timeout=1.0)
        await client.ping()
        await client.aclose()
        return True, "connected"
    except (TimeoutError, RedisError, OSError) as e:
        return False, f"unreachable ({e.__class__.__name__})"


def check_storage() -> str:
    try:
        return get_storage_backend().name
    except StorageError:
        return "unconfigured"


@router.get("/live", response_model=ResponseEnvelope[dict[str, Any]])
async def health_live() -> ResponseEnvelope[dict[str, Any]]:
    """
    Liveness probe: verifies that the FastAPI process is alive and responsive.
    """
    return ResponseEnvelope(
        success=True,
        data={
            "status": "alive",
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.APP_ENV,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@router.get("/ready", response_model=ResponseEnvelope[dict[str, Any]])
async def health_ready(db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Readiness probe: validates backend dependencies (PostgreSQL database, Redis cache/broker, storage).
    """
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except (SQLAlchemyError, OSError):
        db_ok = False
    # Redis is reported but does not gate readiness: reads keep working and
    # POST /inspections/{id}/process answers 503 while the broker is down.
    _redis_ok, redis_status = await check_redis_health()

    checks = {
        "database": "connected" if db_ok else "disconnected",
        "redis": redis_status,
        "storage": check_storage(),
    }

    # In production, DB is strictly required for readiness.
    all_ready = db_ok

    content = ResponseEnvelope(
        success=all_ready,
        data={
            "status": "ready" if all_ready else "not_ready",
            "checks": checks,
            "timestamp": datetime.now(UTC).isoformat(),
        },
        error=None
        if all_ready
        else {
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
