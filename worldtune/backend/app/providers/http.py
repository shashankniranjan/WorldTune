"""Shared outbound HTTP helper for WorldTune's provider adapters.

Same shape as WorldPulse's `http_utils` (timeouts, exponential backoff,
`Retry-After` respect, one User-Agent) but WorldTune's own copy -- the two
products deliberately share no imports.

The client is always obtained from `build_client()` rather than a module
singleton, which is what makes provider parsing testable offline: tests hand
the adapter an `httpx.Client` backed by `httpx.MockTransport` and exercise
the real parsing code against fixture payloads without touching the network.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable, Mapping, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})


class ProviderHTTPError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def build_client(timeout: float | None = None,
                 headers: Mapping[str, str] | None = None) -> httpx.Client:
    merged = {"User-Agent": settings.http_user_agent, "Accept-Encoding": "gzip, deflate"}
    if headers:
        merged.update(headers)
    return httpx.Client(
        timeout=timeout if timeout is not None else settings.http_timeout_seconds,
        headers=merged,
        follow_redirects=True,
    )


def _parse_retry_after(value: str | None) -> float | None:
    if not value:
        return None
    value = value.strip()
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        from datetime import datetime, timezone
        from email.utils import parsedate_to_datetime

        when = parsedate_to_datetime(value)
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        return max(0.0, (when - datetime.now(timezone.utc)).total_seconds())
    except Exception:
        return None


def request_with_retry(
    url: str,
    *,
    params: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
    method: str = "GET",
    client: Optional[httpx.Client] = None,
    max_retries: int | None = None,
    timeout: float | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> httpx.Response:
    """GET/POST with exponential backoff. Non-retryable 4xx raises immediately."""
    retries = settings.http_max_retries if max_retries is None else max_retries
    owns_client = client is None
    active = client or build_client(timeout=timeout, headers=headers)
    last_error: Exception | None = None
    try:
        for attempt in range(retries + 1):
            try:
                response = active.request(method, url, params=params, headers=dict(headers or {}))
            except httpx.HTTPError as exc:
                last_error = exc
                logger.warning("HTTP %s %s failed (%d/%d): %s",
                               method, url, attempt + 1, retries + 1, exc)
            else:
                if response.status_code < 400:
                    return response
                if response.status_code not in RETRYABLE_STATUS:
                    raise ProviderHTTPError(
                        f"{method} {url} -> HTTP {response.status_code}: {response.text[:300]}",
                        status_code=response.status_code,
                    )
                last_error = ProviderHTTPError(
                    f"{method} {url} -> HTTP {response.status_code}",
                    status_code=response.status_code,
                )
                if attempt < retries:
                    retry_after = _parse_retry_after(response.headers.get("Retry-After"))
                    delay = retry_after if retry_after is not None else (
                        settings.http_backoff_base_seconds * (2 ** attempt)
                    )
                    sleep(min(delay, 60.0))
                    continue
            if attempt < retries:
                sleep(min(settings.http_backoff_base_seconds * (2 ** attempt), 60.0))
        raise ProviderHTTPError(
            f"{method} {url} failed after {retries + 1} attempt(s): {last_error}"
        )
    finally:
        if owns_client:
            active.close()


def http_get_json(url: str, **kwargs) -> Any:
    """GET + JSON decode. An empty body is `{}`; an unparseable one is a
    ProviderHTTPError rather than an opaque JSONDecodeError."""
    response = request_with_retry(url, **kwargs)
    body = response.text.strip()
    if not body:
        return {}
    try:
        return response.json()
    except Exception as exc:
        raise ProviderHTTPError(
            f"GET {url} returned non-JSON ({response.headers.get('Content-Type')}): {body[:200]}"
        ) from exc


def http_get_text(url: str, **kwargs) -> str:
    """GET raw body (CSV / RSS feeds)."""
    return request_with_retry(url, **kwargs).text
