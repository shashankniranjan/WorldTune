#!/usr/bin/env python3
"""Discover data.gov.in catalog API UUIDs.

The portal currently exposes catalog cards at /catalogs?page=N.  Its JSON
catalog endpoint is preferred when responsive; the HTML page is retained as a
fallback because the catalog page itself is public and paginated.

This script only inventories catalog metadata. It does not use an API key and
does not download catalog records.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/raw/data_gov_in/catalog_uuid_inventory.json"
BASE = "https://www.data.gov.in"
API = BASE + "/backend/dmspublic/v1/catalogs"
UUID_RE = re.compile(r"/apis/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", re.I)


def load_existing() -> dict[str, dict]:
    if not OUT.exists():
        return {}
    try:
        rows = json.loads(OUT.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return {r["catalog_uuid"]: r for r in rows if isinstance(r, dict) and r.get("catalog_uuid")}


def save(rows: dict[str, dict], page: int) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = sorted(rows.values(), key=lambda x: x["catalog_uuid"])
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(OUT)
    print(f"checkpoint page={page} catalogs={len(payload)} file={OUT}", flush=True)


def from_json(session: requests.Session, rows: dict[str, dict], page_size: int) -> bool:
    """Enumerate the public metadata API, checkpointing every response."""
    from download_data_gov_checkpointed import fetch
    offset = 0
    seen = set()
    while True:
        r = fetch(API, {"limit": page_size, "offset": offset})
        r.raise_for_status()
        obj = r.json()
        candidates = obj.get("data", {}).get("rows", [])
        if not candidates:
            if offset < int(obj.get("total", 0)):
                raise RuntimeError("Premature empty catalog page")
            break
        for item in candidates:
            uid = item["uuid"][0].lower()
            if uid in seen:
                raise RuntimeError("Repeated catalog; inventory changed or pagination failed")
            seen.add(uid)
            rows[uid] = {"catalog_uuid": uid, "source": API, "metadata": item}
        offset += len(candidates)
        save(rows, offset)
        if offset >= int(obj["total"]):
            print(f"Inventory verified: {len(seen)} unique catalogs; API total={obj['total']}")
            break
        time.sleep(3)
    return True


def from_pages(session: requests.Session, rows: dict[str, dict], start: int, end: int, delay: float) -> None:
    for page in range(start, end + 1):
        url = f"{BASE}/catalogs?page={page}"
        for attempt in range(3):
            try:
                r = session.get(url, timeout=(10, 45))
                r.raise_for_status()
                html = r.text
                break
            except requests.RequestException as exc:
                if attempt == 2:
                    print(f"FAILED page={page}: {exc}")
                    html = ""
                else:
                    time.sleep(2 ** attempt)
        found = set(UUID_RE.findall(html))
        for uid in found:
            uid = uid.lower()
            rows[uid] = {"catalog_uuid": uid, "catalog_api_url": f"{BASE}/apis/{uid}", "page": page, "source": "catalogs-page"}
        if page == start or page % 10 == 0 or page == end:
            save(rows, page)
        time.sleep(delay)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start-page", type=int, default=1)
    ap.add_argument("--end-page", type=int, default=1566, help="12,522 catalogs at 8 per page")
    ap.add_argument("--delay", type=float, default=0.25)
    ap.add_argument("--page-size", type=int, default=100)
    ap.add_argument("--pages-only", action="store_true")
    args = ap.parse_args()
    session = requests.Session()
    session.headers.update({"User-Agent": "WorldTune catalog inventory/1.0", "Accept": "text/html,application/json"})
    rows = load_existing()
    if not args.pages_only and args.start_page == 1 and from_json(session, rows, args.page_size):
        return
    from_pages(session, rows, args.start_page, args.end_page, args.delay)
    print(f"DONE catalogs={len(rows)} expected_pages={args.end_page} output={OUT}")


if __name__ == "__main__":
    main()
