#!/usr/bin/env python3
"""Conservative year qualification; candidate retrieval is not year validation."""
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from data_gov_2026 import OUT, ROOT, first
from download_data_gov_checkpointed import save

YEAR = 2026
CUTOFF = datetime(2026, 9, 20)


def years(text):
    return set(map(int, re.findall(r'(?<!\d)(?:19|20)\d{2}(?!\d)', str(text))))


def fiscal(text):
    return bool(re.search(r'(?:19|20)\d{2}\s*[-–/]\s*(?:\d{4}|\d{2})(?![\d/.-])', str(text)))


def future(text):
    for token in re.findall(r'\b2026-\d{2}-\d{2}\b', str(text)):
        try:
            if datetime.strptime(token, '%Y-%m-%d') > CUTOFF:
                return True
        except ValueError:
            pass
    for token in re.findall(r'\b\d{1,2}[-/.]\d{1,2}[-/.]2026\b', str(text)):
        try:
            if datetime.strptime(re.sub(r'[-/.]', '-', token), '%d-%m-%Y') > CUTOFF:
                return True
        except ValueError:
            pass
    return False


def qualify(obj):
    title = obj.get('title', '')
    records = obj.get('records', [])
    fields = obj.get('field', [])
    if re.search(r'project(?:ed|ion)|perspective|budget|estimated.*(?:2026|203\d)', title, re.I):
        return 'projection_or_budget_not_observed', [], 'Title describes projections, estimates or budgets'
    if future(title):
        return 'future_date_needs_review', [], 'Title includes a date after retrieval cutoff'
    date_fields = [f['id'] for f in fields if re.search(r'\b(years?|date|period|month)\b', f.get('name', '').lower()) and not re.search(r'update|publish|creat|birth|age', f.get('name', ''), re.I)]
    # Only treat a field as a row time axis if its values actually contain years.
    date_fields = [f for f in date_fields if any(years(r.get(f, '')) for r in records)]
    if date_fields:
        selected = [r for r in records if any(years(r.get(f, '')) == {YEAR} and not fiscal(r.get(f, '')) and not future(r.get(f, '')) for f in date_fields)]
        return ('calendar_2026_rows' if selected else 'no_calendar_2026_rows_in_download'), selected, 'Row time fields: ' + ', '.join(date_fields)
    year_columns = [f for f in fields if years(f.get('name', ''))]
    current_columns = [f['id'] for f in year_columns if years(f.get('name', '')) == {YEAR} and not fiscal(f.get('name', ''))]
    if current_columns:
        other_years = {f['id'] for f in year_columns if f['id'] not in current_columns}
        selected = [{k: v for k, v in r.items() if k not in other_years} for r in records]
        return 'calendar_2026_columns', selected, 'Kept 2026 columns and identifiers; removed other dated columns'
    if year_columns:
        return 'no_calendar_2026_columns', [], 'Dated columns contain historical or financial-year periods only'
    # Do not turn the date of a parliamentary answer into an observation date.
    if re.search(r'reply|relpy|question|answered', title, re.I):
        return 'observation_date_unverified', [], 'Parliamentary answer date does not establish observation date'
    if years(title) == {YEAR} and not fiscal(title):
        return 'snapshot_or_period_2026', records, 'Reporting period explicitly specified in resource title'
    return 'mixed_period_or_year_unverified', [], 'Fiscal or multi-year periods cannot be isolated as calendar 2026'


def main():
    manifest = json.loads((OUT / 'candidate_manifest.json').read_text())
    audit = {}
    for uid, state in manifest.items():
        entry = dict(state)
        path = OUT / 'candidates' / (uid + '.json')
        if state['status'] == 'retrieved_for_year_audit' and path.exists():
            obj = json.loads(path.read_text())
            category, records, evidence = qualify(obj)
            entry.update(year_status=category, year_rows=len(records), evidence=evidence)
            if records:
                save(OUT / 'verified_2026' / (uid + '.json'), {'resource_uuid': uid, 'catalog_uuid': state['catalog_uuid'], 'title': state['title'], 'qualification': category, 'evidence': evidence, 'source_complete': state.get('complete'), 'retrieval_cutoff': CUTOFF.date().isoformat(), 'records': records})
        else:
            entry.update(year_status='not_retrieved', year_rows=0)
        audit[uid] = entry
    save(OUT / 'year_audit.json', audit)
    catalogs = json.loads((ROOT / 'data/raw/data_gov_in/catalog_uuid_inventory.json').read_text())
    coverage = []
    for catalog in catalogs:
        uid = catalog['catalog_uuid']
        entries = [v for v in audit.values() if v.get('catalog_uuid') == uid]
        coverage.append({'catalog_uuid': uid, 'title': first(catalog['metadata'].get('title')), 'candidates_attempted': len(entries), 'qualified_resources': sum(v['year_rows'] > 0 for v in entries), 'qualified_rows': sum(v['year_rows'] for v in entries), 'coverage': 'candidate_resources_audited' if entries else 'not_audited_no_2026_title_candidate_in_this_run'})
    save(OUT / 'catalog_coverage.json', coverage)
    summary = {'catalog_inventory': len(catalogs), 'title_search_resource_total': json.loads((OUT/'title_2026.json').read_text())['total'], 'resources_attempted': len(audit), 'retrieval_status': dict(Counter(v['status'] for v in audit.values())), 'year_status': dict(Counter(v['year_status'] for v in audit.values())), 'qualified_resources': sum(v['year_rows'] > 0 for v in audit.values()), 'qualified_rows': sum(v['year_rows'] for v in audit.values()), 'qualified_catalogs': sum(v['qualified_resources'] > 0 for v in coverage), 'all_catalog_current_year_complete': False, 'limitations': ['Title search does not find all rolling resources or resources dated only in their records.', 'No 2026 title match is not proof that a catalog lacks 2026 data.', 'Large resource samples are incomplete until pagination is validated.', 'Financial-year aggregates are not calendar-year observations.']}
    save(OUT / 'summary.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
