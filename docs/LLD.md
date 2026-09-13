# WorldPulse -- Low-Level Design

## 1. The point-in-time causality contract

This is the single most important rule in the codebase: **every read used
by the prediction pipeline is bounded by an explicit `as_of` timestamp,
and never returns a row with a timestamp strictly after `as_of`.**

Concretely:

- `database/repository.py::get_events_as_of(session, as_of, since=None)`
  filters `WorldEventORM.occurred_at <= as_of`.
- `database/repository.py::get_bars_as_of(session, symbol, start, as_of)`
  filters `MarketBarORM.timestamp <= as_of`.
- `prediction/predictor.py::create_predictions_for_event(..., as_of)`
  never calls any other repository function; every event, bar, and
  historical outcome it touches is fetched through the two functions
  above.
- A historical event is only used as an analogue for a given
  `(symbol, horizon)` if `event.occurred_at + horizon <= as_of` -- i.e.
  its outcome must already be *resolvable* at prediction time, not just
  "in the past".
- `evaluation/outcome_resolver.py::resolve_predictions(session, provider,
  now)` only resolves predictions whose `event.occurred_at + horizon_hours
  <= now`, and only ever *adds* resolution fields
  (`resolved_at`, `actual_return`, `direction_correct`, `result`) -- it
  never modifies `direction`, `probability`, `expected_return`,
  `median_return`, `p25_return`, `p75_return`, `sample_size`,
  `confidence_tier`, or `created_at`.

`tests/test_no_lookahead.py` is the enforcement test: it runs
`create_predictions_for_event` once, then inserts a dramatic future event
and a future price-spike bar (both timestamped after `as_of`), runs it
again with the *same* `as_of`, and asserts the two results are
bit-for-bit identical (the "prefix test"). It also directly poisons the
DB with future-dated rows and asserts `get_bars_as_of`/`get_events_as_of`
never return them.

`jobs/backfill.py` exercises this contract at the pipeline level: it
walks forward one simulated day at a time, and each day's predictions are
generated using only that day's `as_of` cutoff -- there is no code path
that lets a later day "go back" and revise an earlier day's prediction.

## 2. Core schemas

### `WorldEvent` (pydantic, `events/schemas.py`)

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | deterministic (uuid5 of the source item id), so re-classifying the same raw item is idempotent |
| `source_id` | `str` | id of the raw news/intel item |
| `occurred_at` | `datetime` | when the event happened (drives all causality checks) |
| `ingested_at` | `datetime` | when WorldPulse saw it |
| `event_type` | `EventDomain` enum | one of 5 domains (see below) |
| `event_subtype` | `str` | keyword-derived refinement, e.g. `missile_strike` |
| `countries`, `entities`, `affected_channels` | `list[str]` | structured tags used for filtering/re-ranking |
| `potential_assets` | `list[str]` | instrument symbols this event could plausibly move |
| `severity` | `float` [0,1] | |
| `reasoning_summary` | `str` | why the classifier assigned these tags |
| `headline`, `source_confidence`, `corroboration_count` | | |
| `event_cluster_id` | `str \| None` | shared id for near-duplicate events (dedup) |
| `embedding` | `list[float] \| None` | deterministic hashing-trick vector |

`EventDomain`: `conflict_geopolitical`, `military_activity`,
`energy_disruption`, `economic_policy`, `natural_disaster`.

### `MarketBar` (dataclass, `ingestion/markets.py::Bar`)

`symbol, timestamp, open, high, low, close, volume, source`.

### `Prediction` (SQLAlchemy ORM, `database/models.py::PredictionORM`)

Split explicitly into **immutable** fields (set once, at creation) and
**resolution** fields (set later, only by the outcome resolver):

Immutable: `id, event_id, symbol, horizon_hours, direction, probability,
expected_return, median_return, p25_return, p75_return, sample_size,
confidence_tier, event_domain, explanation_json, created_at`.

Resolution: `resolved_at, actual_return, direction_correct, result`.

### Postgres+pgvector note

`WorldEventORM.embedding` is a `Text` column here (JSON-encoded
`list[float]`), because SQLite has no vector type. In a Postgres
deployment it would be declared as `pgvector.sqlalchemy.Vector(128)`
instead, and `similarity/embeddings.py::cosine_similarity` would be
replaced by a `<=>` operator query for approximate nearest-neighbor
search at scale. The rest of the schema (indexes, foreign keys, column
types) is written to work unchanged against Postgres -- see
`database/models.py::UTCDateTime`, which stores/reads datetimes
consistently as UTC on both backends.

## 3. Module-by-module notes

### `ingestion/`

- `providers/`: the event-source layer. `base.py` defines the
  `WorldEventProvider` port (`fetch_events(start, end) -> list[WorldEvent]`,
  `name`, `is_available()`) plus a `ProviderHealth` record each adapter
  updates on every call, and the separate `ContextDataProvider` port for
  time-series sources. `registry.py` reads `EVENT_PROVIDERS` (default
  `gdelt,usgs,eonet,gdacs` — all keyless), instantiates only providers
  whose `is_available()` is True, refuses paid providers while
  `WORLDPULSE_MODE=free`, and logs every skip with its reason. Adapters:
  `gdelt.py` (DOC 2.0 API, one query per event domain), `usgs.py` (FDSN
  event query for history + summary feed for live; magnitude→severity with
  floors at M6/M7/M8), `eonet.py` (v3 category→subtype map), `gdacs.py`
  (EVENTS4APP GeoJSON with an RSS fallback; alert level *is* the severity
  signal), `firms.py` (fire pixels clustered spatio-temporally into
  wildfire events), `acled.py` (OAuth password grant, optional),
  `fred.py`/`eia.py` (context series only — deliberately **not**
  `WorldEventProvider`, so a weekly inventory print never becomes a
  meaningless `WorldEvent`), and `worldmonitor.py` (the paid API wrapped as
  one optional provider, plus `SyntheticEventProvider` for the offline
  demo).
- `http_utils.py`: the single HTTP path every provider uses — timeout,
  exponential backoff, `Retry-After` respect, shared User-Agent. Providers
  obtain clients through `build_client()` so tests can substitute an
  `httpx.MockTransport`.
- `worldmonitor.py`: `WorldMonitorClient` port with 6 methods matching the
  spec (`get_news_intelligence`, `get_conflict_events`,
  `get_energy_intelligence`, `get_intel_timeline`,
  `search_intel_history`, `get_similar_events`). `MockWorldMonitorClient`
  pre-generates a fixed-size (4000 item), fixed-epoch (2020-01-01,
  spanning ~10 years) deterministic superset keyed only by `seed`, then
  every query just filters that superset by date range. This matters:
  because the superset doesn't depend on the query's own start/end, the
  same historical timestamp always yields the same synthetic event
  regardless of what "now" a caller queries with -- required for
  walk-forward backfill to be meaningful (otherwise day 5's view of day
  3's events could differ from day 3's own view of itself).
- `markets.py`: `MarketDataProvider` port — **unchanged** by the
  free-data refactor, so prediction/evaluation stay decoupled from where
  prices come from. Free keyless implementations were added alongside the
  default: `BinancePublicMarketProvider` (`/api/v3/klines`, real hourly
  crypto) and `StooqMarketProvider` (daily CSV for indices/futures/FX/ETFs
  — daily only, so it cannot evaluate the sub-daily horizons).
  `SyntheticMarketDataProvider`
  generates a geometric-random-walk per symbol from a fixed epoch, using
  a per-`(seed, symbol, step-index)` hash-seeded RNG -- so, like the news
  generator, overlapping queries for the same symbol always agree
  bar-for-bar.

### `events/`

- `classifier.py`: `RuleBasedEventClassifier` maps a source category hint
  to an `EventDomain`, refines `event_subtype` via headline keyword
  matching, and derives `potential_assets` from a per-domain static
  table. Deterministic id via `uuid5(NAMESPACE_URL, "worldpulse-event:" +
  source_id)`.
- `deduplication.py`: union-find clustering. Two events merge into the
  same `event_cluster_id` iff `|occurred_at_a - occurred_at_b| <=
  window_hours` AND `cosine_similarity(embed_a, embed_b) >
  similarity_threshold` AND they share at least one entity or country.
- `entity_resolution.py`: small alias table (`"US"` -> `"USA"`, etc.)
  applied before comparison so trivial name variants don't block
  clustering.
- `schemas.py`: also hosts `impact_candidate_score` (see formula below).

### `markets/`

- `returns.py`: `compute_event_window_returns(bars, event_time)` computes
  pre-windows (-24h/-8h/-1h) and post-horizons (+1h/+4h/+8h/+12h/+24h) as
  simple returns, using `bisect` against a pre-sorted timestamp list for
  O(log n) lookups (this matters: analogue retrieval calls this once per
  historical event, so a linear scan would make the whole pipeline
  intractable at more than a few hundred events).
- `abnormal_returns.py`: `rolling_baseline_volatility(bars, event_time)`
  computes the population stdev of consecutive-bar returns strictly
  *before* `event_time` (never touching the event window or anything
  after); `abnormal_return = event_return / baseline_volatility`.

### `similarity/`

- `embeddings.py`: hashing-trick bag-of-words over
  `type/subtype/country/entity/channel` tokens, L2-normalized, dimension
  128. No network access, no model download.
- `retrieval.py`: `structured_filter` (same `event_type`, severity within
  tolerance) then `top_k_by_embedding` (cosine similarity, top K).
- `ranking.py`: re-ranks the retrieved set by
  `0.5*embedding_similarity + 0.2*event_type_match + 0.1*geo_similarity +
  0.1*severity_similarity + 0.1*channel_similarity`.

### `prediction/`

- `model.py`: `compute_distribution_stats(outcomes)` takes
  `[(similarity_weight, realized_return), ...]` and computes weighted
  `p_up`, weighted mean, and weighted median/p25/p75 (via cumulative
  weight thresholds over the value-sorted list).
- `confidence.py`: tier assignment, checked in this exact order:
  1. `sample_size < min_sample_size (10)` -> `NO_PREDICTION`
  2. `no_signal_low (0.45) <= probability <= no_signal_high (0.55)` ->
     `NO_PREDICTION` (checked *before* the tier thresholds, so a huge
     sample with a coin-flip probability is still `NO_PREDICTION`)
  3. `sample_size >= 30 and probability >= 0.70` -> `HIGH`
  4. `sample_size >= 15 and probability >= 0.62` -> `MEDIUM`
  5. `sample_size >= 10 and probability >= 0.57` -> `LOW`
  6. otherwise -> `NO_PREDICTION`
- `predictor.py`: `generate_prediction(...)` is a pure function over
  already-fetched, already causally-filtered data (no DB/clock access) --
  this is what the leakage tests call directly.
  `create_predictions_for_event(...)` is the DB/market-data-aware
  orchestrator: it fetches each symbol's bars *once* and reuses the
  sorted list across every historical analogue and horizon (see
  `_bars_for_symbol`/`_resolved_return_from_bars`), which is what keeps
  the retrieval step tractable.
- `baseline.py`: Baseline A (always UP), Baseline B (momentum
  continuation of the preceding 1h move), Baseline C (historical
  unconditional P(up), computed only from data available before the
  evaluation point).
- `features.py`: builds `ImpactScoreInputs` from an event plus the recent
  event window (for novelty).

### `impact_candidate_score` formula

```
score = 0.30*severity + 0.20*corroboration + 0.15*novelty
      + 0.15*historical_market_relevance + 0.10*geographic_relevance
      + 0.10*source_confidence
```

All six inputs and the output are clamped to `[0, 1]`.
`corroboration = min(corroboration_count / 5, 1)`. `novelty = 1 -
max(cosine_similarity(event, e) for e in recent_events)`.
`historical_market_relevance` is a static per-domain prior (e.g. energy
disruption = 0.85, natural disaster = 0.55). `geographic_relevance` is
boosted per major-economy country mentioned. Gate: `score >= 0.60`
(`IMPACT_THRESHOLD`) or the event is skipped entirely -- no prediction
rows are created for it, for any symbol or horizon.

### `evaluation/`

- `outcome_resolver.py`: for each unresolved prediction whose horizon has
  elapsed by `now`, computes the realized return (bars fetched/sorted
  once per `(event, symbol)` pair, shared across the up-to-5 horizons for
  that pair) and sets only the resolution fields.
- `scoring.py`: `compute_scoreboard` -- coverage, directional accuracy,
  precision by confidence tier, accuracy by horizon, accuracy by event
  domain, and baseline accuracies (Baseline A / historical-majority
  stand-in for Baseline C) over the same resolved sample.
- `calibration.py`: buckets resolved directional predictions by stated
  probability (50-60%, 60-70%, ..., 90-100%) and compares mean stated
  probability to realized accuracy per bucket; `calibration_error` is a
  size-weighted mean absolute difference (a simple ECE-style metric).

### `agents/`

- `investigator.py`: `TemplatedInvestigator` (default) fills
  `observed_facts / historical_association / ai_hypothesis / prediction /
  what_would_invalidate` from the event and `PredictionResult` directly --
  no LLM call. `LLMInvestigator` is a pluggable skeleton using the same
  prompts (`prompts.py`) when `OPENAI_API_KEY` is set.

### `api/` and `database/repository.py`

Routes are thin: they open a session (via
`get_default_session_factory()`, a process-wide cached engine/session
factory), run a repository query or evaluation function, and serialize.
No business logic lives in `api/routes.py`.

## 4. Known simplifications (see also README "what's mocked vs real")

- Analogue matching uses raw simple returns, not the volatility-
  normalized abnormal returns computed in `markets/abnormal_returns.py`
  (that module is fully implemented and unit-tested, just not yet wired
  into `predictor.py`'s outcome computation).
- Baseline B (momentum continuation) is implemented
  (`prediction/baseline.py::baseline_momentum`) but not wired into
  `evaluation/scoring.py`'s scoreboard, since the current `PredictionORM`
  schema doesn't persist the pre-event 1h return; the scoreboard reports
  Baseline A and a historical-majority stand-in for Baseline C.
- Embeddings are a hashing-trick bag-of-words vector, not a trained
  semantic model.
