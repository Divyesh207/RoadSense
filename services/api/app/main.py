from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.middleware import RequestTrackingMiddleware
from app.schemas.common import ErrorDetail, ResponseEnvelope, ResponseMeta


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend API service for road damage detection, analysis, maintenance, and verification.",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(RequestTrackingMiddleware)

if settings.CORS_ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Standard Exception Handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    request_id = getattr(request.state, "request_id", None)
    if isinstance(exc.detail, dict):
        code = exc.detail.get("code", f"HTTP_{exc.status_code}")
        message = exc.detail.get("message", "An error occurred")
        details = exc.detail.get("details")
    else:
        code = f"HTTP_{exc.status_code}"
        message = str(exc.detail)
        details = None

    return JSONResponse(
        status_code=exc.status_code,
        content=ResponseEnvelope(
            success=False,
            error=ErrorDetail(
                code=code,
                message=message,
                details=details,
            ),
            meta=ResponseMeta(request_id=request_id),
        ).model_dump(mode="json"),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ResponseEnvelope(
            success=False,
            error=ErrorDetail(
                code="VALIDATION_ERROR",
                message="Request validation failed",
                details=exc.errors(),
            ),
            meta=ResponseMeta(request_id=request_id),
        ).model_dump(mode="json"),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ResponseEnvelope(
            success=False,
            error=ErrorDetail(
                code="INTERNAL_SERVER_ERROR",
                message="An unexpected server error occurred.",
                details=str(exc) if settings.DEBUG else None,
            ),
            meta=ResponseMeta(request_id=request_id),
        ).model_dump(mode="json"),
    )


# API Routers
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Root"])
async def root():
    return {
        "message": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "api_v1": settings.API_V1_PREFIX,
    }
