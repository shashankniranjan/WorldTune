"""Bounded metadata lookup for exact publisher URLs discovered by GDELT."""
from __future__ import annotations

from functools import lru_cache
from html.parser import HTMLParser

import httpx

from app.config import settings


class _MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title: str | None = None
        self.image: str | None = None
        self.description: str | None = None
        self._in_title = False
        self._title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): (value or "") for key, value in attrs}
        if tag.lower() == "title":
            self._in_title = True
        if tag.lower() != "meta":
            return
        key = (values.get("property") or values.get("name") or "").lower()
        content = values.get("content", "").strip()
        if key in {"og:title", "twitter:title"} and content:
            self.title = self.title or content
        elif key in {"og:image", "twitter:image", "twitter:image:src"} and content:
            self.image = self.image or content
        elif key in {"description", "og:description"} and content:
            self.description = self.description or content

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False
            if not self.title:
                self.title = " ".join(self._title_parts).strip() or None

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data.strip())


@lru_cache(maxsize=4096)
def get_publisher_metadata(url: str) -> tuple[str | None, str | None, str | None]:
    """Fetch only the supplied URL; failure is a nullable metadata result."""
    try:
        with httpx.Client(timeout=min(1.5, max(0.75, settings.http_timeout_seconds)), follow_redirects=True,
                          headers={"User-Agent": settings.http_user_agent}) as client:
            response = client.get(url, headers={"Range": "bytes=0-262143"})
            response.raise_for_status()
        parser = _MetadataParser()
        parser.feed(response.text[:262144])
        return parser.title, parser.image, parser.description
    except Exception:
        return None, None, None
