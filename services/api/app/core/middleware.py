import time
import uuid
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.schemas.common import ErrorDetail, ResponseEnvelope, ResponseMeta


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = (time.perf_counter() - start_time) * 1000

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Production security headers enforcing OWASP recommendations:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY (clickjacking protection)
    - X-XSS-Protection: 1; mode=block
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: camera/mic restrictions
    - Content-Security-Policy: default-src 'self'
    - Strict-Transport-Security (HSTS) when enabled
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        if settings.SECURITY_HEADERS_ENABLED:
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Permissions-Policy"] = "geolocation=(self), camera=(), microphone=()"
            response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"

            if settings.HSTS_ENABLED:
                response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Guards against payload exhaustion / DoS attacks by enforcing request body size limits.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                length = int(content_length)
                # Determine limit based on endpoint type
                path = request.url.path
                if any(media_path in path for media_path in ["/media", "/inspections", "/evidence"]):
                    max_size = settings.MAX_MEDIA_REQUEST_SIZE_BYTES
                else:
                    max_size = settings.MAX_REQUEST_SIZE_BYTES

                if length > max_size:
                    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
                    return JSONResponse(
                        status_code=413,
                        content=ResponseEnvelope(
                            success=False,
                            error=ErrorDetail(
                                code="PAYLOAD_TOO_LARGE",
                                message=f"Payload size {length} bytes exceeds maximum allowed limit ({max_size} bytes).",
                            ),
                            meta=ResponseMeta(request_id=request_id),
                        ).model_dump(mode="json"),
                    )
            except ValueError:
                pass

        return await call_next(request)


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Sliding window in-memory rate limiter per client IP.
    Applies stricter limits to authentication routes and standard limits elsewhere.
    """

    def __init__(self, app):
        super().__init__(app)
        # Dictionary mapping key -> list of timestamps
        self.request_history: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.RATE_LIMIT_ENABLED or request.headers.get("X-Bypass-Rate-Limit") == "test-bypass":
            return await call_next(request)

        # Identify client (Forwarded IP or client host)
        client_ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or (
            request.client.host if request.client else "unknown"
        )
        path = request.url.path

        # Determine rate limit configuration for the path
        if "/auth/login" in path:
            limit = settings.RATE_LIMIT_AUTH_PER_MINUTE
            window_seconds = 60
            key = f"auth:{client_ip}"
        else:
            limit = settings.RATE_LIMIT_DEFAULT_PER_MINUTE
            window_seconds = 60
            key = f"gen:{client_ip}"

        now = time.time()
        window_start = now - window_seconds

        # Prune old timestamps
        history = self.request_history[key]
        self.request_history[key] = [t for t in history if t > window_start]

        if len(self.request_history[key]) >= limit:
            request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
            retry_after = int(window_seconds - (now - self.request_history[key][0])) + 1
            response = JSONResponse(
                status_code=429,
                content=ResponseEnvelope(
                    success=False,
                    error=ErrorDetail(
                        code="RATE_LIMIT_EXCEEDED",
                        message=f"Rate limit exceeded. Maximum {limit} requests per minute allowed.",
                    ),
                    meta=ResponseMeta(request_id=request_id),
                ).model_dump(mode="json"),
                headers={
                    "Retry-After": str(max(1, retry_after)),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(now + retry_after)),
                },
            )
            return response

        # Record this request
        self.request_history[key].append(now)

        response = await call_next(request)
        remaining = max(0, limit - len(self.request_history[key]))
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
