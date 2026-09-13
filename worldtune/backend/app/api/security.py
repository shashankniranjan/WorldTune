"""Request-level safety: timeout, in-process rate limiting, input sanitization
(spec section 33).

Deliberately infrastructure-free -- no Redis, no gateway. The rate limiter is
a per-process sliding window in memory. Its limitation is stated rather than
hidden: with N workers the effective limit is N x the configured value, and
counters reset on restart. That is the correct tradeoff for a prototype whose
non-negotiable requirement is running with zero external services; the
production answer is a shared store, and the interface here does not change
when that arrives.
"""
from __future__ import annotations

import asyncio
import re
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


class RateLimiter:
    """Sliding-window counter keyed by client IP."""

    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)

    def check(self, key: str, *, now: float | None = None) -> tuple[bool, int]:
        now = now if now is not None else time.monotonic()
        bucket = self._hits[key]
        cutoff = now - self.window
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= self.limit:
            retry_after = int(max(1, self.window - (now - bucket[0])))
            return False, retry_after
        bucket.append(now)
        return True, 0

    def reset(self) -> None:
        self._hits.clear()


_limiter = RateLimiter(settings.rate_limit_requests, settings.rate_limit_window_seconds)


def get_limiter() -> RateLimiter:
    return _limiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in {"/health", "/docs", "/openapi.json", "/redoc"}:
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        allowed, retry_after = _limiter.check(client)
        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded", "retry_after_seconds": retry_after},
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)


class TimeoutMiddleware(BaseHTTPMiddleware):
    """Bound every request so a slow provider or a pathological query cannot
    hold a connection open indefinitely."""

    def __init__(self, app, timeout_seconds: float | None = None):
        super().__init__(app)
        self.timeout = timeout_seconds or settings.request_timeout_seconds

    async def dispatch(self, request: Request, call_next):
        try:
            return await asyncio.wait_for(call_next(request), timeout=self.timeout)
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content={"detail": f"Request exceeded {self.timeout:.0f}s budget"},
            )


# --- input sanitization ------------------------------------------------------

# Allow letters, digits, spaces and a small punctuation set. Everything else is
# dropped rather than escaped: these values reach ILIKE patterns and JSON
# responses, and a whitelist is the only rule that stays correct as the sinks
# change.
_ALLOWED_RE = re.compile(r"[^\w\s\-\.\+#&/,']", re.UNICODE)
MAX_QUERY_LENGTH = 120


def sanitize_query(value: str | None, *, max_length: int = MAX_QUERY_LENGTH) -> str:
    """Whitelist-clean a free-text query parameter."""
    if value is None:
        return ""
    cleaned = _ALLOWED_RE.sub(" ", str(value))
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) > max_length:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Query too long (max {max_length} characters)",
        )
    return cleaned


def clamp_limit(value: int | None, *, default: int = 10, maximum: int = 100) -> int:
    if value is None:
        return default
    return max(1, min(int(value), maximum))
