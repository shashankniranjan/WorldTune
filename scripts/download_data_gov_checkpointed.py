#!/usr/bin/env python3
"""Serial, resumable resource downloads; never persist credentials."""
import argparse
import getpass
import hashlib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlencode

import requests

ROOT = Path(__file__).resolve().parents[1]


def fetch(url, params):
    config = 'url = ' + json.dumps(url + '?' + urlencode(params)) + '\n'
    result = subprocess.run(['curl', '--config', '-', '--max-time', '30', '--max-filesize', '50000000', '-sS', '-i'], input=config.encode(), capture_output=True)
    if result.returncode:
        raise requests.ConnectionError('curl transport failure')
    headers, body = result.stdout.split(b'\r\n\r\n', 1)
    headers = headers.decode('iso-8859-1')
    response = requests.Response()
    response.status_code = int(headers.splitlines()[0].split()[1])
    response._content = body
    for line in headers.splitlines()[1:]:
        if ':' in line:
            name, value = line.split(':', 1)
            response.headers[name] = value.strip()
    return response


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n')
    tmp.replace(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--inventory', type=Path, default=ROOT / 'data/raw/data_gov_in/discovered_resource_uuids.json')
    ap.add_argument('--output', type=Path, default=ROOT / 'data/raw/data_gov_in/checkpointed_api')
    ap.add_argument('--delay', type=float, default=3)
    ap.add_argument('--max-pages', type=int, default=10, help='Per resource per run; resume larger resources in subsequent runs')
    args = ap.parse_args()
    key = os.environ.get('DATA_GOV_IN_API_KEY') or getpass.getpass('API key: ')
    manifest_path = args.output / 'manifest.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    last = 0
    consecutive_failures = 0
    for item in json.loads(args.inventory.read_text()):
        uid = item['uuid']
        state = manifest.setdefault(uid, {'status': 'pending', 'offset': 0, 'pages': [], 'slug': item.get('slug')})
        if state['status'] == 'complete' and state.get('total') == 0:
            state.update(status='pending', pages=[], offset=0)
        if state['status'] == 'complete':
            continue
        pages_this_run = 0
        while True:
            time.sleep(max(0, max(3, args.delay) - (time.monotonic() - last)))
            last = time.monotonic()
            try:
                r = fetch(f'https://api.data.gov.in/resource/{uid}', {'api-key': key, 'format': 'json', 'limit': 1000, 'offset': state['offset']})
                if r.status_code == 429:
                    retry = r.headers.get('Retry-After', '60')
                    try:
                        delay = float(retry)
                    except ValueError:
                        delay = (parsedate_to_datetime(retry) - datetime.now(timezone.utc)).total_seconds()
                    state.update(status='throttled', retry_after_seconds=max(60, delay))
                    save(manifest_path, manifest)
                    print('Throttled; saved checkpoint. Resume after', max(60, delay), 'seconds.', flush=True)
                    return
                if r.status_code in (401, 403):
                    state.update(status='authorization_failed', http=r.status_code)
                    save(manifest_path, manifest)
                    return
                r.raise_for_status()
                obj = r.json()
                if obj.get('status') != 'ok':
                    state.update(status='api_error', error_message=str(obj.get('message', 'Unknown API error')).replace(key, '[REDACTED]'))
                    save(manifest_path, manifest)
                    print(uid, state['status'], state['error_message'], flush=True)
                    break
                if 'records' not in obj or not isinstance(obj['records'], list):
                    raise ValueError('Missing records array')
                records = obj['records']
                total = int(obj['total']) if obj.get('total') is not None else None
                digest = hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest()
                if records and any(p['sha256'] == digest for p in state['pages']):
                    raise ValueError('Repeated page')
                if not records and total is not None and state['offset'] < total:
                    raise ValueError('Premature empty page')
                # Persist only a parsed response with the credential redacted everywhere.
                obj = json.loads(json.dumps(obj).replace(key, '[REDACTED]'))
                path = args.output / uid / f"{state['offset']:012d}.json"
                save(path, obj)
                state['pages'].append({'offset': state['offset'], 'rows': len(records), 'sha256': digest, 'file': str(path)})
                state['offset'] += len(records)
                state['total'] = total
                state['status'] = 'complete' if (total is not None and state['offset'] >= total) or not records else 'partial'
                state.pop('error', None)
                pages_this_run += 1
                consecutive_failures = 0
            except (requests.RequestException, ValueError, TypeError) as exc:
                state.update(status='failed', error=type(exc).__name__)
                consecutive_failures += 1
            save(manifest_path, manifest)
            print(uid, state['status'], 'rows=', state['offset'], flush=True)
            if state['status'] != 'partial':
                break
            if pages_this_run >= args.max_pages:
                print('Per-run page budget reached; checkpoint retained.', flush=True)
                break
        if consecutive_failures >= 3:
            print('Circuit breaker: three consecutive failures; remaining resources unattempted.', flush=True)
            break


if __name__ == '__main__':
    main()
