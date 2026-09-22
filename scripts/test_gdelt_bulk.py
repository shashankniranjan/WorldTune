#!/usr/bin/env python3
"""Small, resumable GDELT bulk validation (never calls the DOC API).

GAL is preferred when an official index exposes the requested window.  GDELT
currently publishes no usable GAL index on the bulk host, so this script
selects GKG from the indexed gdeltv2 master file list.  GKG is article-level
enough for this validation and includes URL, source, language, themes,
entities, locations and tone.
"""
from __future__ import annotations

import argparse, csv, gzip, hashlib, io, json, logging, re, time, zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/gdelt"
PROCESSED = ROOT / "data/processed/gdelt"
INDEX_URL = "https://data.gdeltproject.org/gdeltv2/masterfilelist.txt"
UA = "WorldPulse-GDELT-bulk-validation/1.0"
log = logging.getLogger("gdelt_bulk")


def norm_url(value: str) -> str:
    try:
        p = urlsplit((value or "").strip())
        host = p.netloc.lower().split("@")[-1]
        if host.startswith("www."): host = host[4:]
        path = re.sub(r"/+$", "", p.path or "/")
        return urlunsplit((p.scheme.lower(), host, path, p.query, ""))
    except Exception:
        return (value or "").strip().lower()


def fetch(url: str, dest: Path, attempts: int = 4) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        return True
    for attempt in range(attempts):
        try:
            with requests.get(url, headers={"User-Agent": UA}, timeout=(15, 120), stream=True) as r:
                if r.status_code == 404:
                    (RAW / "failed_urls.log").open("a").write(f"{url}\tHTTP 404 (indexed but not yet available)\n")
                    return False
                r.raise_for_status()
                tmp = dest.with_suffix(dest.suffix + ".part")
                with tmp.open("wb") as f:
                    for chunk in r.iter_content(1024 * 1024):
                        if chunk: f.write(chunk)
                tmp.replace(dest)
                return True
        except Exception as exc:
            if attempt == attempts - 1:
                (RAW / "failed_urls.log").open("a").write(f"{url}\t{exc}\n")
                raise
            time.sleep(min(60, 2 ** attempt * 2))


def discover_gkg(start: datetime, end: datetime) -> list[tuple[datetime, str]]:
    r = requests.get(INDEX_URL, headers={"User-Agent": UA}, timeout=(15, 180))
    r.raise_for_status()
    out = []
    for line in r.text.splitlines():
        parts = line.split()
        if len(parts) != 3 or ".gkg.csv.zip" not in parts[2]: continue
        name = parts[2].rsplit("/", 1)[-1]
        try: stamp = datetime.strptime(name[:14], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
        except ValueError: continue
        if start <= stamp < end: out.append((stamp, parts[2].replace("http://", "https://")))
    return sorted(set(out))


def parse_file(path: Path) -> list[dict]:
    rows = []
    with zipfile.ZipFile(path) as z:
        member = z.namelist()[0]
        with z.open(member) as raw:
            for line in io.TextIOWrapper(raw, encoding="utf-8", errors="replace"):
                cols = line.rstrip("\n").split("\t")
                if len(cols) < 27: continue
                # GKG v2.1: article title is not a native field.  URL, source,
                # themes, locations, people, organizations and tone are.
                translation = cols[21] if len(cols) > 21 else ""
                lang = ""
                m = re.search(r"(?:srclc|sourceLanguage):([^;,#]+)", translation, re.I)
                if m: lang = m.group(1)
                rows.append({"timestamp": cols[1], "url": cols[4], "title": "",
                    "domain": cols[3], "source_country": "", "language": lang,
                    "themes": cols[7], "locations": cols[8], "persons": cols[9],
                    "organizations": cols[10], "tone": cols[11], "source_file": path.name})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--days", type=int, default=15); ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args(); logging.basicConfig(level=logging.INFO, format="%(message)s")
    RAW.mkdir(parents=True, exist_ok=True); PROCESSED.mkdir(parents=True, exist_ok=True)
    end = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    start = end - timedelta(days=args.days)
    files = discover_gkg(start, end)
    if not files: raise SystemExit("No indexed GKG files found in requested window")
    log.info("Dataset: GKG (GAL index unavailable; DOC API not used)\nWindow: %s -> %s\nFiles: %d", start, end, len(files))
    rows=[]; compressed=0
    # Four concurrent downloads keeps the run practical while remaining a
    # deliberately low request rate; each URL is still fetched only once.
    def download_one(item):
        _, url = item; dest = RAW / url.rsplit("/", 1)[-1]
        if not fetch(url, dest): return None
        return dest, parse_file(dest)
    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, 16))) as pool:
        futures = [pool.submit(download_one, item) for item in files]
        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            if result is None: continue
            dest, parsed = result; compressed += dest.stat().st_size; rows.extend(parsed)
            if i % 10 == 0 or i == len(files): log.info("[%d/%d] %s records=%d", i, len(files), dest.name, len(rows))
    df=pd.DataFrame(rows); df["published_at"]=pd.to_datetime(df.timestamp, format="%Y%m%d%H%M%S", utc=True, errors="coerce")
    df["normalized_url"]=df.url.map(norm_url); df=df[df.normalized_url!=""].drop_duplicates("normalized_url", keep="first")
    out=PROCESSED/f"gdelt_gkg_{start:%Y%m%d}_{end:%Y%m%d}.parquet"; df.to_parquet(out,index=False)
    raw_count=len(rows); unique=len(df); extracted=out.stat().st_size; days=max(1,args.days)
    successful_files = len(list(RAW.glob("*.gkg.csv.zip")))
    stats={"dataset":"GKG","window_utc":[start.isoformat(),end.isoformat()],"files_indexed":len(files),"files_downloaded":successful_files,"failed_or_unavailable_files":len(files)-successful_files,"compressed_bytes":compressed,"processed_bytes":extracted,"raw_records":raw_count,"unique_articles":unique,"duplicate_percent":round((raw_count-unique)*100/raw_count,3) if raw_count else 0,"records_per_day":dict((str(k.date()),int(v)) for k,v in df.groupby("published_at",dropna=True).size().items()),"top_domains":Counter(df.domain.dropna()).most_common(20),"top_source_countries":Counter(df.source_country.dropna()).most_common(20),"languages":Counter(df.language.dropna()).most_common(),"min_timestamp":str(df.published_at.min()),"max_timestamp":str(df.published_at.max()),"avg_compressed_mb_day":compressed/1024/1024/days,"avg_processed_mb_day":extracted/1024/1024/days,"estimated_6_month_mb":compressed/1024/1024/days*182.5,"estimated_1_year_mb":compressed/1024/1024/days*365,"fields_available":[c for c in df.columns if c not in {"source_file","normalized_url"}]}
    (PROCESSED/"report.json").write_text(json.dumps(stats,indent=2,default=str)); print(json.dumps(stats,indent=2,default=str))

if __name__ == "__main__": main()
