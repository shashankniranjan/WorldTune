#!/usr/bin/env python3
"""Discover data.gov.in resource UUIDs from public slugs and download via API.

The API key is read only from DATA_GOV_IN_API_KEY and is never written to disk.
This script does not automate or bypass CAPTCHA-protected portal downloads.
"""
from __future__ import annotations
import concurrent.futures
import hashlib
import json
import os
import re
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/raw/data_gov_in/api_downloads"
SLUGS = [
    "all-india-level-worker-population-ratios-wpr-during-2018-ministry-statistics-and-programme",
    "year-wise-estimated-worker-population-ratio-wpr-and-unemployment-rate-ur-2017-18-2019-20",
    "stateut-wise-details-worker-population-ratio-wpr-persons-age-15-years-and-above-during",
    "year-wise-worker-population-ratio-wpr-indicating-employment-usual-status-various-age",
    "stateut-wise-estimated-worker-population-ratio-wpr-persons-age-15-59-years-2019-20-2021-22",
    "stateut-wise-details-rural-worker-population-ratio-wpr-usual-status-persons-age-15-years",
    "stateut-wise-details-working-population-ratio-wpr-persons-age-15-years-and-above-2020-21",
    "stateut-wise-worker-population-ratio-wpr-according-usual-status-psss-during-2017-18",
    "sector-wise-share-employment-plfs-during-2019-20",
    "year-wise-results-annual-periodic-labour-force-survey-plfs-conducted-during-2018-19-and",
    "year-wise-migration-rate-national-service-scheme-nss-64th-round-during-july-2007-june-2008",
    "stateut-wise-details-unemployment-rate-usual-status-psss-estimated-periodic-labour-force",
    "estimates-unemployment-rate-periodic-labour-force-survey-plfs-annual-report-2017-18-2018",
    "year-wise-unemployment-rate-among-people-completed-school-education-college-education",
    "year-wise-results-periodic-labour-force-survey-plfs-conducted-ministry-statistics-and",
    "year-wise-details-percentage-distribution-rural-workers-broad-industry-division-periodic",
    "year-wise-details-unemployment-rate-ur-usual-status-periodic-labour-force-survey-plfs",
    "religious-group-wise-details-labour-force-participation-women-periodic-labour-force-survey",
]
UUID_RE = re.compile(rb"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")

def discover(slug: str) -> dict:
    try:
        r = requests.get(f"https://data.gov.in/resource/{slug}", timeout=(5, 15))
        ids = UUID_RE.findall(r.content)
        return {"slug": slug, "uuid": ids[0].decode() if ids else None, "page_http": r.status_code}
    except Exception as e:
        return {"slug": slug, "uuid": None, "error": type(e).__name__}

def download(item: dict, key: str) -> dict:
    uuid = item.get("uuid")
    if not uuid:
        return {**item, "api_http": None, "status": "uuid_not_found"}
    path = OUT / f"{uuid}.json"
    if path.exists() and path.stat().st_size:
        b = path.read_bytes()
        return {**item, "api_http": 200, "status": "already_present", "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()}
    try:
        r = requests.get(f"https://api.data.gov.in/resource/{uuid}", params={"api-key": key, "format": "json", "limit": 100000}, timeout=(3, 12))
        if r.status_code != 200:
            return {**item, "api_http": r.status_code, "status": "failed", "error": r.text[:200]}
        path.write_bytes(r.content)
        return {**item, "api_http": r.status_code, "status": "downloaded", "bytes": len(r.content), "sha256": hashlib.sha256(r.content).hexdigest()}
    except Exception as e:
        return {**item, "api_http": None, "status": "failed", "error": type(e).__name__}

def main() -> int:
    key = os.environ.get("DATA_GOV_IN_API_KEY")
    if not key:
        raise SystemExit("DATA_GOV_IN_API_KEY is required")
    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path = ROOT / "data/raw/data_gov_in/discovered_resource_uuids.json"
    if manifest_path.exists():
        discovered = json.loads(manifest_path.read_text())
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
            discovered = list(ex.map(discover, SLUGS))
    results = []
    for item in discovered:
        result = download(item, key)
        results.append(result)
        (OUT / "manifest.json").write_text(json.dumps({"source": "data.gov.in API", "results": results}, indent=2) + "\n")
    manifest = {"source": "data.gov.in API", "results": results}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
