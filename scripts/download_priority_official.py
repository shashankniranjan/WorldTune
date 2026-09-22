#!/usr/bin/env python3
"""Download directly published official WorldTune priority source files.

This intentionally does not automate CAPTCHA-protected data.gov.in downloads.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "worldtune_priority" / "official"
SOURCES = [
    ("mospi", "plfs_2017_18_annual_report.pdf", "https://mospi.gov.in/sites/default/files/publication_reports/Annual%20Report%2C%20PLFS%202017-18_31052019.pdf"),
    ("labour", "eshram_data_sharing_guidelines.pdf", "https://labour.gov.in/sites/default/files/data_sharing_guidelines_statesuts_0.pdf"),
    ("labour", "eshram_pib_2025_employment.pdf", "https://labour.gov.in/sites/default/files/pib2098444.pdf"),
    ("labour", "eshram_pib_2021_10_crore.pdf", "https://labour.gov.in/sites/default/files/pib1776993.pdf"),
    ("labour", "eshram_pib_2022_implementation.pdf", "https://labour.gov.in/sites/default/files/pib1809231.pdf"),
]

def fetch(url: str, path: Path) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 0:
        data = path.read_bytes()
        return {"url": url, "path": str(path.relative_to(ROOT)), "status": "already_present", "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    last = None
    for attempt in range(1, 4):
        try:
            with requests.get(url, timeout=(20, 120), stream=True, headers={"User-Agent": "WorldTune-public-source-validation/1.0"}) as r:
                r.raise_for_status()
                with path.open("wb") as f:
                    for chunk in r.iter_content(1024 * 1024):
                        if chunk:
                            f.write(chunk)
            data = path.read_bytes()
            return {"url": url, "path": str(path.relative_to(ROOT)), "status": "downloaded", "http": r.status_code, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        except Exception as exc:
            last = repr(exc)
            if path.exists():
                path.unlink()
            if attempt < 3:
                time.sleep(2 ** (attempt - 1))
    return {"url": url, "path": str(path.relative_to(ROOT)), "status": "failed", "error": last}

def main() -> int:
    results = [fetch(url, OUT / group / name) for group, name, url in SOURCES]
    manifest = {"generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "results": results}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))
    return 0 if all(x["status"] in {"downloaded", "already_present"} for x in results) else 1

if __name__ == "__main__":
    raise SystemExit(main())
