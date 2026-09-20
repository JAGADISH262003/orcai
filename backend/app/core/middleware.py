"""ASGI middleware: request correlation, access logs, security headers, rate limiting."""

import logging
import time
import uuid
from collections import defaultdict
from threading import Lock

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import request_id_var

logger = logging.getLogger("orcai.http")


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assign a request id, expose it on the response, and emit an access log line."""

    def __init__(self, app):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        token = request_id_var.set(request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            raise
        finally:
            request_id_var.reset(token)

        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "%s %s %d (%s)",
            request.method,
            request.url.path,
            response.status_code,
            request.url.query or "",
            extra={
                "_json": {
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "duration_ms": duration_ms,
                    "ip": client_ip(request),
                }
            },
        )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), camera=(), microphone=()",
        "Cross-Origin-Opener-Policy": "same-origin",
    }

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if get_settings().SECURITY_HEADERS:
            for k, v in self.HEADERS.items():
                response.headers.setdefault(k, v)
        return response


class _Bucket:
    __slots__ = ("tokens", "updated", "burst")

    def __init__(self, burst: float) -> None:
        self.tokens = burst
        self.burst = burst
        self.updated = time.monotonic()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory token-bucket rate limiter keyed by client IP.

    Bypassed entirely when RL_ENABLED=false. Webhook endpoints get relaxed
    limits (they are authenticated via signature, not the IP).
    """

    def __init__(self, app):
        super().__init__(app)
        self._buckets: dict[str, _Bucket] = defaultdict(lambda: _Bucket(0))
        self._lock = Lock()
        self._last_cleanup = time.monotonic()

    def _refill(self, key: str, bucket: _Bucket, rate: float) -> None:
        now = time.monotonic()
        bucket.tokens = min(bucket.tokens + (now - bucket.updated) * rate, bucket.burst)
        bucket.updated = now

    def _hit(self, key: str, burst: float, rate: float) -> bool:
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                # Fresh bucket starts full so the first request is allowed.
                bucket = self._buckets[key] = _Bucket(burst)
            else:
                bucket.burst = burst
                self._refill(key, bucket, rate)
            if bucket.tokens >= 1:
                bucket.tokens -= 1
                return True
            return False

    async def dispatch(self, request: Request, call_next):
        st = get_settings()
        if not st.RL_ENABLED:
            return await call_next(request)

        key = client_ip(request)
        if request.url.path in ("/health", "/ready") or request.url.path.endswith("/webhook"):
            return await call_next(request)

        rate = st.RL_REQUESTS_PER_MINUTE / 60.0
        if not self._hit(key, float(st.RL_BURST), rate):
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please slow down."},
                headers={"Retry-After": "1"},
            )
        return await call_next(request)
