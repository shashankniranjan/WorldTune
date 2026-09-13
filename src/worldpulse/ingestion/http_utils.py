"""Shared HTTP helper for every ingestion provider.

One place for: timeouts, exponential backoff with jitter-free deterministic
sleeps, `Retry-After` header respect, and a consistent User-Agent. Every
provider adapter calls `http_get_json` / `http_get_text` from here rather
than talking to `httpx` directly, so retry/timeout behaviour is uniform
and trivially patchable in tests.

Tests patch `worldpulse.ingestion.http_utils.build_client` (or pass an
explicit `client=` into a provider constructor) with an
`httpx.MockTransport`-backed client, which is why the client is always
obtained through a factory function instead of a module-level singleton.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Callable, Mapping, Optional

import httpx

from worldpulse.config import settings

logger = logging.getLogger(__name__)

# HTTP statuses worth retrying: transient server errors + explicit throttles.
RETRYABLE_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})


class ProviderHTTPError(RuntimeError):
    """Raised when a request ultimately fails after all retries."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def build_client(timeout: float | None = None, headers: Mapping[str, str] | None = None) -> httpx.Client:
    """Construct a fresh `httpx.Client` with WorldPulse defaults."""
    merged = {"User-Agent": settings.http_user_agent, "Accept-Encoding": "gzip, deflate"}
    if headers:
        merged.update(headers)
    return httpx.Client(
        timeout=timeout if timeout is not None else settings.http_timeout_seconds,
        headers=merged,
        follow_redirects=True,
    )


def _parse_retry_after(value: str | None) -> float | None:
    """`Retry-After` may be delta-seconds or an HTTP-date; we honour both,
    falling back to None when unparseable."""
    if not value:
        return None
    value = value.strip()
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        from email.utils import parsedate_to_datetime
        from datetime import datetime, timezone

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
    """Issue a request, retrying transient failures with exponential backoff.

    Backoff is `http_backoff_base_seconds * 2**attempt`, overridden by a
    server-supplied `Retry-After` when present. Raises `ProviderHTTPError`
    if every attempt fails; a non-retryable 4xx raises immediately.
    """
    retries = settings.http_max_retries if max_retries is None else max_retries
    owns_client = client is None
    active = client or build_client(timeout=timeout, headers=headers)
    last_error: Exception | None = None
    try:
        for attempt in range(retries + 1):
            try:
                response = active.request(method, url, params=params, headers=dict(headers or {}))
            except httpx.HTTPError as exc:  # timeouts, DNS, connection resets
                last_error = exc
                logger.warning("HTTP %s %s failed (attempt %d/%d): %s",
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
                logger.warning("HTTP %s %s -> %d (attempt %d/%d)", method, url,
                               response.status_code, attempt + 1, retries + 1)
                retry_after = _parse_retry_after(response.headers.get("Retry-After"))
                if attempt < retries:
                    delay = retry_after if retry_after is not None else (
                        settings.http_backoff_base_seconds * (2 ** attempt)
                    )
                    sleep(min(delay, 60.0))
                    continue

            if attempt < retries:
                sleep(min(settings.http_backoff_base_seconds * (2 ** attempt), 60.0))

        raise ProviderHTTPError(f"{method} {url} failed after {retries + 1} attempt(s): {last_error}")
    finally:
        if owns_client:
            active.close()


def http_get_json(url: str, **kwargs) -> Any:
    """GET a URL and JSON-decode the body.

    Several of the open feeds we consume (GDELT in particular) return
    `text/html` or an empty body on an empty result set, so decoding is
    guarded and an unparseable body is reported as a provider error rather
    than an opaque `JSONDecodeError`.
    """
    response = request_with_retry(url, **kwargs)
    body = response.text.strip()
    if not body:
        return {}
    try:
        return response.json()
    except Exception as exc:
        raise ProviderHTTPError(
            f"GET {url} returned non-JSON body ({response.headers.get('Content-Type')}): "
            f"{body[:200]}"
        ) from exc


def http_get_text(url: str, **kwargs) -> str:
    """GET a URL and return the raw body as text (CSV / XML feeds)."""
    return request_with_retry(url, **kwargs).text
