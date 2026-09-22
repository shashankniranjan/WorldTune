#!/usr/bin/env python3
"""Audit public resource metadata and retrieve candidates for calendar 2026."""
import argparse
import csv
import io
import getpass
import json
import os
import re
import time
from urllib.parse import urlparse
from pathlib import Path

from download_data_gov_checkpointed import ROOT, fetch, save

OUT = ROOT / 'data/raw/data_gov_in/year_2026'
BASE = 'https://www.data.gov.in/backend/dmspublic/v1'
KEEP = ['uuid', 'catalog_uuid', 'catalog_title', 'title', 'note', 'frequency',
        'is_api_available', 'is_webservice', 'node_alias', 'datafile', 'file_size',
        'field_resource_type', 'sector', 'sector_resource', 'domain', 'changed']


def first(v, default=''):
    return v[0] if isinstance(v, list) and v else default


def inventory(size):
    folder = OUT / 'inventory'
    offset = 0
    seen = set()
    missing_uuid = []
    while True:
        path = folder / f'{offset:09d}.json'
        if path.exists():
            obj = json.loads(path.read_text())
        else:
            r = fetch(BASE + '/resources_noaggs', {'limit': size, 'offset': offset})
            r.raise_for_status()
            body = r.json()
            if body.get('statusCode') != 200 or 'data' not in body:
                raise ValueError('Invalid metadata response')
            obj = {'offset': offset, 'total': body['total'], 'rows': [{k: row[k] for k in KEEP if k in row} for row in body['data']['rows']]}
            if not obj['rows'] and offset < int(obj['total']):
                raise ValueError('Premature empty metadata page')
            save(path, obj)
            time.sleep(3)
        for row in obj['rows']:
            uid = first(row.get('uuid'))
            if not uid:
                missing_uuid.append(row)
                continue
            if uid in seen:
                raise ValueError('Duplicate resource across metadata pages')
            seen.add(uid)
        offset += len(obj['rows'])
        print('resource metadata', offset, '/', obj['total'], flush=True)
        if offset >= int(obj['total']):
            save(OUT / 'missing_resource_uuids.json', missing_uuid)
            save(OUT / 'inventory_status.json', {'status': 'complete', 'unique_resources': len(seen), 'missing_uuid': len(missing_uuid), 'api_total': obj['total']})
            break


def classify():
    groups = {'mentions_2026': [], 'rolling_or_undated': [], 'historical_metadata': []}
    seen = set()
    paths = sorted((OUT / 'inventory').glob('*.json')) + [OUT / 'title_2026.json', OUT / 'webservices.json']
    for path in paths:
        if not path.exists():
            continue
        for row in json.loads(path.read_text())['rows']:
            uid = first(row.get('uuid'))
            if not uid or uid in seen:
                continue
            seen.add(uid)
            title = first(row.get('title'))
            # Discovery only: title dates and parliamentary answer dates are NOT
            # sufficient evidence that the underlying observations are in 2026.
            text = title + ' ' + first(row.get('note'))
            if re.search(r'\b2026\b|2025[-–/]26\b', text):
                group = 'mentions_2026'
            elif first(row.get('is_webservice'), 0) in (1, '1') or not re.search(r'\b(?:19|20)\d{2}\b', title):
                group = 'rolling_or_undated'
            else:
                group = 'historical_metadata'
            groups[group].append(row)
    for name, rows in groups.items():
        save(OUT / (name + '.json'), rows)
    print({k: len(v) for k, v in groups.items()}, flush=True)


def sample():
    key = os.environ.get('DATA_GOV_IN_API_KEY') or getpass.getpass('API key: ')
    rows = json.loads((OUT / 'title_2026.json').read_text())['rows']
    # Round robin by catalog so broad coverage comes before depth.
    buckets = {}
    for row in rows:
        buckets.setdefault(first(row.get('catalog_uuid')), []).append(row)
    rows = []
    while any(buckets.values()):
        for bucket in buckets.values():
            if bucket:
                rows.append(bucket.pop(0))
    manifest_path = OUT / 'candidate_manifest.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    failures = 0
    for row in rows:
        uid = first(row['uuid'])
        if uid in manifest and manifest[uid]['status'] not in ('api_error', 'failed'):
            continue
        state = {'title': first(row['title']), 'catalog_uuid': first(row.get('catalog_uuid')), 'status': 'pending'}
        # Try actual resource API even when portal's is_api_available flag is 0:
        # this flag is not sufficient evidence of API availability.
        try:
            file_url = first(row.get('datafile'))
            use_file = first(row.get('is_api_available')) == '0' and urlparse(file_url).hostname == 'www.data.gov.in' and urlparse(file_url).path.lower().endswith('.csv') and int(first(row.get('file_size'), 0)) <= 10_000_000
            if use_file:
                # Public download URL returned by the metadata API; no login or
                # CAPTCHA automation. Keep this transport distinct in the audit.
                r = fetch(file_url, {})
            else:
                r = fetch('https://api.data.gov.in/resource/' + uid, {'api-key': key, 'format': 'json', 'offset': 0, 'limit': 1000})
            if r.status_code in (429, 401):
                state.update(status='blocked', http=r.status_code, retry_after=r.headers.get('Retry-After'))
                manifest[uid] = state
                save(manifest_path, manifest)
                return
            if r.status_code == 403:
                state.update(status='access_denied', http=403)
                manifest[uid] = state
                save(manifest_path, manifest)
                time.sleep(3)
                continue
            r.raise_for_status()
            if use_file:
                try:
                    text = r.content.decode('utf-8-sig')
                    state['source_encoding'] = 'utf-8-sig'
                except UnicodeDecodeError:
                    text = r.content.decode('cp1252')
                    state['source_encoding'] = 'cp1252'
                if text.lstrip().startswith('<'):
                    raise ValueError('Expected CSV; received HTML')
                reader = csv.DictReader(io.StringIO(text))
                records = list(reader)
                if not reader.fieldnames or any(None in record for record in records):
                    raise ValueError('Malformed CSV')
                obj = {'status': 'ok', 'title': state['title'], 'catalog_uuid': state['catalog_uuid'], 'total': len(records), 'records': records, 'field': [{'id': name, 'name': name} for name in reader.fieldnames], 'source_file_url': file_url}
                state['transport'] = 'public_csv_link_from_metadata_api'
            else:
                obj = r.json()
                state['transport'] = 'resource_api'
            if obj.get('status') != 'ok':
                state.update(status='api_error', message=str(obj.get('message')).replace(key, '[REDACTED]'))
            else:
                records = obj.get('records', [])
                state.update(status='retrieved_for_year_audit', total=obj.get('total'), rows=len(records), complete=len(records) == int(obj['total']))
                save(OUT / 'candidates' / (uid + '.json'), json.loads(json.dumps(obj).replace(key, '[REDACTED]')))
            failures = 0
        except Exception as exc:
            state.update(status='failed', error=type(exc).__name__)
            failures += 1
        manifest[uid] = state
        save(manifest_path, manifest)
        print(uid, state['status'], state.get('rows'), flush=True)
        if failures >= 3:
            return
        time.sleep(3)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['inventory', 'classify', 'sample'])
    ap.add_argument('--page-size', type=int, default=5000)
    args = ap.parse_args()
    if args.mode == 'inventory':
        inventory(args.page_size)
    elif args.mode == 'classify':
        classify()
    else:
        sample()
