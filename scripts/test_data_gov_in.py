#!/usr/bin/env python3
"""Small data.gov.in resource/API validation; key is read from the environment."""
from __future__ import annotations

import argparse, json, logging, os, time
from pathlib import Path
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/data_gov_in"
OUT = ROOT / "data/processed/data_gov_in"
BASE = "https://api.data.gov.in/resource/"
RESOURCES = {
    "employment_exchanges_monthly": {
        "uuid": "05c95863-884d-4981-a000-8f7d603eb586",
        "title": "Monthly data of employment exchanges from July 2012 to April 2013",
    },
    "employment_exchanges_annual": {
        "uuid": "c1a57cdc-c3de-4829-9ffb-3139a93d181",
        "title": "Annual live registration of job seekers in employment exchanges from 2002 to 2011",
    },
}

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=1000)
    ap.add_argument("--resource", choices=sorted(RESOURCES), help="test exactly one resource")
    ap.add_argument("--recursive", action="store_true", help="test every approved resource sequentially")
    args = ap.parse_args()
    key = os.getenv("DATA_GOV_IN_API_KEY")
    if not key: raise SystemExit("DATA_GOV_IN_API_KEY is required and is never written to disk")
    RAW.mkdir(parents=True, exist_ok=True); OUT.mkdir(parents=True, exist_ok=True)
    session = requests.Session(); session.headers.update({"User-Agent":"WorldPulse-data-gov-in-test/1.0"})
    report = {"source":"data.gov.in","generated_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"resources":[]}
    selected = [args.resource] if args.resource else list(RESOURCES)
    if not args.recursive and not args.resource:
        selected = list(RESOURCES)  # backwards-compatible default: approved manifest only
    for name in selected:
        meta = RESOURCES[name]; url = BASE + meta["uuid"]
        item={"name":name,"uuid":meta["uuid"],"title":meta["title"],"endpoint":url}
        try:
            r = session.get(url, params={"api-key":key,"format":"json","limit":args.limit}, timeout=(15,60))
            item["http_status"] = r.status_code; r.raise_for_status(); payload=r.json()
            (RAW/f"{name}.json").write_text(json.dumps(payload,indent=2))
            records=payload.get("records",[]); item.update({"raw_records":len(records),"fields":list(records[0]) if records else [],"total_available":payload.get("total")})
            if records:
                df=pd.DataFrame(records); df.to_parquet(OUT/f"{name}.parquet",index=False); item["processed_bytes"]=(OUT/f"{name}.parquet").stat().st_size
        except Exception as exc:
            item["status"]="FAILED"; item["error"]=str(exc)
        report["resources"].append(item)
        print(json.dumps(item,indent=2))
    (OUT/"report.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__ == "__main__": main()
