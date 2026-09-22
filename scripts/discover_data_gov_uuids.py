#!/usr/bin/env python3
import json, re
from pathlib import Path
import requests

SLUGS = [
    "all-india-level-worker-population-ratios-wpr-during-2018-ministry-statistics-and-programme",
    "year-wise-estimated-worker-population-ratio-wpr-and-unemployment-rate-ur-2017-18-2019-20",
    "stateut-wise-details-worker-population-ratio-wpr-persons-age-15-years-and-above-during",
    "year-wise-worker-population-ratio-wpr-indicating-employment-usual-status-various-age",
    "stateut-wise-estimated-worker-population-ratio-wpr-persons-age-15-59-years-2019-20-2021-22",
    "stateut-wise-details-rural-worker-population-ratio-wpr-usual-status-persons-age-15-years",
    "stateut-wise-details-working-population-ratio-wpr-persons-age-15-years-and-above-2020-21",
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

def main():
    out = []
    for slug in SLUGS:
        try:
            r = requests.get(f"https://data.gov.in/resource/{slug}", timeout=(5, 15))
            uuids = re.findall(rb"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", r.content)
            out.append({"slug": slug, "uuid": uuids[0].decode() if uuids else None, "http": r.status_code})
        except Exception as e:
            out.append({"slug": slug, "uuid": None, "error": type(e).__name__})
    path = Path("data/raw/data_gov_in/discovered_resource_uuids.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
