# WorldTune current state

Last validated: 20 September 2026

This document describes what is currently present and tested in the WorldPulse repository. It is a prototype data-validation and personalization layer, not a production data platform or trading system.

## Current persona

The seeded WorldTune persona is:

- Senior/data engineer working in European technology consulting
- Based in Bengaluru, India
- Interests: crypto, AI, technology regulation, and data engineering
- Crypto watchlist: BTC and ETH
- Declared holdings/exposures: gold, silver, and HINDALCO

Holdings are labels used for relevance and impact explanations. Quantities, cost basis, broker credentials, and account information are not stored.

## Data currently available

### GDELT

The repository contains a bounded GDELT GKG download covering approximately 4–19 September 2026:

- Raw compressed files: `data/raw/gdelt/`
- Processed Parquet: `data/processed/gdelt/gdelt_gkg_20260904_20260919.parquet`
- Raw records: 1,414,108
- Unique articles after normalized-URL deduplication: 1,412,784
- Duplicate percentage: 0.094%
- Raw compressed size: approximately 6.1 GB
- Processed Parquet size: approximately 1.2 GB
- Files indexed: 1,440
- Files downloaded: 1,430
- Files unavailable: 10

Available GKG fields include timestamp, URL, domain, themes, locations, people, organizations, and tone-related columns. The current extract has unreliable or empty title, language, and source-country values, so these fields must be improved before relying on them for high-quality summaries.

GDELT DOC API was not used. No API key was used.

### data.gov.in

A bounded resource test exists in `scripts/test_data_gov_in.py`.

Validated resource:

- Monthly employment-exchange data: 10 records retrieved and saved locally

The portal-wide catalogue was not downloaded. Some data.gov.in resource downloads require interactive CAPTCHA or portal interaction and were not bypassed.

### Official public documents

The following direct official file was downloaded:

- PLFS 2017–18 annual report: approximately 19.4 MB
- Location: `data/raw/worldtune_priority/official/mospi/`

The downloader and manifest are:

- `scripts/download_priority_official.py`
- `data/raw/worldtune_priority/official/manifest.json`

Some Labour Ministry PDF URLs found in indexed search results now return 404 after site redirects. They remain source-resolution work, not confirmed data gaps.

## Current impact-analysis code

The bounded analysis command is:

```bash
python3 scripts/worldtune_impact_sample.py
```

It reads the existing GDELT Parquet and writes:

- `data/processed/worldtune/impact_sample/report.md`
- `data/processed/worldtune/impact_sample/report.json`

The current topic pulse uses deterministic keyword matching across GDELT URL, themes, organizations, and locations fields.

Latest generated sample:

| Topic | Records | Share |
|---|---:|---:|
| Crypto | 26,228 | 1.86% |
| Technology | 41,085 | 2.91% |
| Macro/policy | 54,252 | 3.84% |

The report includes a holding-impact map:

- Gold: real yields, USD, inflation, geopolitical risk
- Silver: industrial demand, solar/electronics, USD, real yields
- HINDALCO: aluminium/copper, energy costs, manufacturing, INR, European demand, China demand

## Deterministic versus AI-generated output

The current standalone report is deterministic. It was generated locally by Python and did not call OpenRouter.

The repository already has an optional WorldTune LLM explainer at:

- `worldtune/backend/app/llm/explainer.py`

The backend accepts `OPENROUTER_API_KEY` as an alias for its LLM key. It defaults to:

```text
Base URL: https://openrouter.ai/api/v1
Model: openai/gpt-4o-mini
```

The intended AI flow is:

```text
GDELT evidence
  -> deterministic topic counts
  -> persona and holdings relevance
  -> market observations
  -> confidence and limitations
  -> AI-written explanation
```

The AI layer must summarize supplied evidence only. It must not invent prices, holdings, returns, or causal relationships.

## Current limitations

- No aligned 15-day BTC/ETH market series is present. Only a 10-hour Binance smoke-test sample exists for 19 September.
- Therefore market correlation is currently reported as `insufficient`.
- GDELT GKG is metadata-oriented and does not reliably provide full article text.
- Current keyword counts are recall-oriented and may include syndicated or irrelevant mentions.
- Source-country and language fields are empty in the current extract.
- No event clustering, fact verification, or source-quality weighting has been applied to this sample.
- No investment recommendation or automated trade signal is produced.
- No full 10-year employment, PLFS, e-Shram, RBI, CPI, or NSS historical store exists yet.

## Recommended next validation step

Before treating WorldTune as an impact or correlation product:

1. Download aligned BTCUSDT, ETHUSDT, gold, silver, HINDALCO, INR/USD, INR/EUR, and relevant index prices for the GDELT window.
2. Improve GKG parsing and validate column positions against the official schema.
3. Add source-quality weighting and event deduplication beyond URL deduplication.
4. Generate daily topic and holding features.
5. Run lagged correlations and walk-forward tests.
6. Compare AI summaries with the deterministic evidence and retain citations.

The correct product interpretation at this stage is: **personalized news context with an impact map**, not a validated predictive trading system.

## Implemented next slice: local Silver and Gold layers

The first incremental slice of the proposed Bronze/Silver/Gold design is now implemented in
`scripts/build_worldtune_layers.py`. It reads the validated GDELT GKG Parquet extract and
writes deterministic local Parquet outputs under `data/processed/worldtune/layers/`:

- `silver_articles.parquet`: normalized timestamps, provenance, normalized-URL deduplication,
  a transparent source-quality prior, and deterministic topic flags
- `gold_daily_topic_metrics.parquet`: daily article volume, topic counts, and mean source-quality prior
- `gold_daily_entity_metrics.parquet`: daily topic/entity counts
- `gold_source_metrics.parquet`: daily source-domain counts and quality prior
- `manifest.json`: input path, row counts, UTC coverage, deduplication key, and limitations

Run it with:

```bash
python3 scripts/build_worldtune_layers.py
```

The current run produced 1,412,784 Silver rows from 1,412,784 input rows covering
2026-09-04T18:45Z through 2026-09-19T17:45Z. The first day is partial because that is how the
bounded source extract begins. This slice remains descriptive: GKG metadata is not article text,
topic matches are recall-oriented, and source quality is an explicit prior rather than fact
verification. DuckDB, PostgreSQL, dbt, embeddings, and LLM reasoning are intentionally not yet
required by this local validation step.

The next signal-candidate step is implemented in `scripts/build_worldtune_signals.py`:

```bash
python3 scripts/build_worldtune_signals.py
```

It writes `data/processed/worldtune/signals/gold_signal_candidates.parquet`, a latest JSON
snapshot, and a manifest. For each aggregate it computes a prior-7-day baseline, z-score, and
day-over-day momentum; the current day is excluded from its own baseline. The first three
observations are explicitly marked `insufficient_history`. These are news-volume candidates,
not price or investment signals.

## Signal Evidence layer

Per `docs/requirement.md`, the next layer is implemented in
`scripts/build_worldtune_evidence.py`:

```bash
python3 scripts/build_worldtune_evidence.py
```

It reads the existing candidate and Silver artifacts and writes:

- `data/processed/worldtune/evidence/gold_signal_evidence.parquet`
- `data/processed/worldtune/evidence/validation_summary.json`
- `data/processed/worldtune/evidence/manifest.json`

The evidence table contains article/domain counts, normalized domain diversity, top GKG themes,
organizations, people, locations and domains, up to 20 domain-diverse representative URLs,
3-day/7-day anomaly and persistence metrics, acceleration, configurable component scores, and
the weighted `signal_strength`. The V1 weights are anomaly 0.40, volume growth 0.25, persistence
0.20, and source diversity 0.15. The summary records the exact score definitions and limitations.

The current run produced 78 evidence rows from 96 candidates, with 0 missing-evidence rows.
This remains a single-source GDELT evidence layer: it does not claim cross-source confirmation,
causality, event discovery, or article-text understanding.

## User-facing World Shift layer

The evidence layer now feeds `scripts/build_world_shifts.py`, which performs transparent
subtopic discovery from the supplied GDELT records and writes
`data/processed/worldtune/world_shifts/gold_world_shifts.parquet` plus `world_state.json`.
Broad `all` is excluded from user-facing shifts. A topic is emitted only when its detector
matches at least three records; direction is preserved separately from strength (`SURGING`,
`RISING`, `COOLING`, `FALLING`, or `STABLE`). Blank source titles receive a UI-safe fallback.

Named topics now have independent causal attention histories instead of inheriting their broad
category score. Geopolitics is a first-class category with armed-conflict, sanctions,
energy/trade-route disruption, and diplomatic-crisis detectors. Ranking is based on:

- `impact_gravity_score = 0.60 * world_impact_score + 0.40 * persona_impact_score`
- `priority_score = 0.50 * impact_gravity_score + 0.35 * signal_strength + 0.15 * evidence_quality_score`

`world_impact_score` combines an explicit topic-severity prior with observed domain breadth and
persistence. `persona_impact_score` is an explicit relevance prior for the seeded India-based
data/AI, European technology, crypto, gold/silver/HINDALCO profile. `signal_strength` remains the
named topic's anomaly/growth/persistence/diversity score. All priors and weights are stored in
the validation summary; they are product-policy judgements, not facts learned from GDELT.

The current run generated 105 discovery candidates across nine observed subtopics. They are
not verified events: relationships are same-day `associated_with` links, and technology and
finance impact views are explicitly marked unsupported because this dataset has no developer,
jobs, market, or company evidence.

The backend exposes the artifact through:

- `GET /world/shifts`
- `GET /world/shifts/{shift_id}`
- `GET /world/shifts/{shift_id}/evidence`
- `GET /world/shifts/{shift_id}/relationships`
- `GET /world/shifts/{shift_id}/tech-impact`
- `GET /world/shifts/{shift_id}/finance-impact`

The canonical backend also runs a cache-first snapshot refresh automatically every hour. The
existing ACTIVE snapshot remains readable while publisher enrichment and AI generation run in
the background; completed snapshots are stored in the database and promoted atomically. Read
requests never contact publisher sites. If no matching database snapshot exists, the portal
immediately renders the deterministic artifact with `Headline unavailable` placeholders.

This hourly job currently refreshes enrichment and AI snapshots from the latest local World
Shift artifact. Fetching newly published GDELT bulk files and rebuilding that artifact remains a
separate ingestion concern; do not interpret the hourly snapshot schedule as fresh source-data
coverage.

## One-year GDELT baseline

`scripts/download_gdelt_year_sample.py` adds a disk-safe one-year GKG baseline. It selected the
indexed file nearest 12:00 UTC for each day from 2025-09-20 through 2026-09-19, downloaded 365
files, and produced `data/processed/gdelt/gdelt_gkg_year_sample_20250920_20260919.parquet`.
The sample contains 392,078 raw records and 392,006 URL-deduplicated articles. It is explicitly
one file per day, not the complete 15-minute GDELT archive; the complete archive is estimated at
roughly 140-150 GB compressed and did not fit the available local disk.

The year-specific rebuilt pipeline is under `data/processed/worldtune/year/` and contains 2,190
candidate rows, 2,172 evidence rows, and 1,932 discovered World Shift candidates. Run the
download and rebuild commands with explicit paths before replacing the shorter validation
artifacts.
