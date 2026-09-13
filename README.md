# WorldPulse

WorldPulse turns a stream of real-world events (conflict, military
activity, energy disruption, economic/policy announcements, natural
disasters) into market-impact predictions: for each event, it finds
historically similar past events, looks at what actually happened to
~18 financial instruments afterward, and produces a direction/
probability/expected-return/confidence-tier prediction for 5 time
horizons (1h/4h/8h/12h/24h). A background resolver later fills in what
actually happened, and a scoring layer reports how good the predictions
really are versus simple baselines.

**WorldPulse runs at zero cost, with no API keys and no paid
subscriptions.** Events come from open public feeds (GDELT, USGS, NASA
EONET, GDACS), market data from Binance's and Stooq's free public
endpoints, and event classification from a deterministic rule engine that
needs no LLM. Everything below the "FREE QUICK START" line works with an
empty `.env`.

---

## FREE QUICK START

No account, no key, no card. Four commands:

```bash
git clone <your-fork-url> && cd WorldPulse
cp .env.example .env                 # every value in it is optional
pip install -e ".[dev]"

# 1. Prove it works, fully offline (92 tests, no network):
pytest -q

# 2. Run the deterministic walk-forward demo (prints "DATA MODE: FREE"
#    and a full scoreboard). Uses the offline synthetic event source, so
#    it needs no network at all:
python -m jobs.backfill --days 20

# 3. Start the API and the dashboard:
uvicorn apps.api.main:app --reload        # -> http://localhost:8000/docs
streamlit run apps/dashboard/app.py       # -> click "Run demo pipeline"
```

Docker instead of a local Python env:

```bash
cp .env.example .env && docker compose up
```

Check which data sources are live and which are switched off:

```bash
curl localhost:8000/health              # -> {"data_mode": "FREE", ...}
curl localhost:8000/health/providers    # per-provider HEALTHY/DEGRADED/DISABLED
```

### Ingest real events from the free feeds

```bash
# Live poll of every open feed (no keys needed):
python -m jobs.ingest_world_events --providers gdelt,usgs,eonet,gdacs --lookback-days 1

# Real historical backfill (USGS reaches back to 1900):
python -m jobs.backfill --start 2024-01-01 --end 2024-03-01 --providers usgs,eonet
```

Before relying on the live endpoints, confirm they are reachable from your
machine:

```bash
python scripts/verify_live_providers.py --all
```

### What each data source costs

**Group 1 — no key, no registration, no cost.** These are the defaults.

| Provider | Data | `EVENT_PROVIDERS` name |
|---|---|---|
| GDELT DOC 2.0 | Global news across all five event domains | `gdelt` |
| USGS (FDSN + feeds) | Earthquakes, with history back to 1900 | `usgs` |
| NASA EONET v3 | Wildfires, storms, volcanoes, floods | `eonet` |
| GDACS | Multi-hazard disaster alerts with severity scoring | `gdacs` |
| Binance public klines | Real hourly crypto OHLCV (`MARKET_DATA_PROVIDER=binance`) | — |
| Stooq CSV | Daily OHLCV for indices/futures/FX/ETFs (`MARKET_DATA_PROVIDER=stooq`) | — |
| Synthetic generator | Deterministic offline events + prices (demo/tests) | `synthetic` |

**Group 2 — free, but needs a free registration key.** Each is zero cost
and instantly issued. Leave the key blank and the provider disables itself
cleanly; nothing breaks.

| Provider | Data | Env var | Register at |
|---|---|---|---|
| NASA FIRMS | Active-fire detections, clustered into wildfires | `NASA_FIRMS_API_KEY` | <https://firms.modaps.eosdis.nasa.gov/api/> |
| FRED | Macro time series (*context/feature only, not events*) | `FRED_API_KEY` | <https://fredaccount.stlouisfed.org/apikeys> |
| EIA | Energy time series (*context/feature only, not events*) | `EIA_API_KEY` | <https://www.eia.gov/opendata/> |
| ACLED | Political violence / protests, 1997→present | `ACLED_EMAIL` + `ACLED_PASSWORD` | <https://acleddata.com/register/> |

**Group 3 — optional, PAID.**

| Provider | Env var | Status |
|---|---|---|
| World Monitor intel API | `WORLDMONITOR_API_KEY` | Entirely optional. Not in the default `EVENT_PROVIDERS`, and refused outright while `WORLDPULSE_MODE=free` (the default). WorldPulse is fully functional with this unset — see `tests/test_no_worldmonitor_required.py`. |

Full details per provider — historical depth, update frequency, rate
limits, data-quality caveats, fallback behaviour — are in
[`docs/data-sources.md`](docs/data-sources.md).

---

## Architecture in one paragraph

Every event source implements one port, `WorldEventProvider`
(`src/worldpulse/ingestion/providers/base.py`), so the pipeline is
decoupled from which feeds are configured. `EVENT_PROVIDERS` selects them;
the registry instantiates only those whose `is_available()` is True and
logs the rest as skipped. Providers normalize into the single `WorldEvent`
model, the rule-based classifier enriches them from
`config/impact_channels.yaml`, and cross-source deduplication merges
records from *different* providers describing the same real-world event
(time proximity + haversine distance + type compatibility + entity
overlap), writing one `EventEvidence` row per contributing source so
nothing is dropped. From there the pre-existing pipeline is unchanged:
analogue retrieval → return distribution → confidence tiering →
persistence → outcome resolution → scoreboard.

## Running the demo pipeline manually (step by step)

Instead of `jobs/backfill.py`, you can drive the same stages one at a
time, at any simulated timestamp, which is what the dashboard's "Run demo
pipeline" button and `jobs/backfill.py` both do under the hood. Run each
with `-m` (or set `PYTHONPATH=.`) so `jobs` resolves as a package:

```bash
python -m jobs.ingest_world_events --now 2024-01-01T00:00:00 --lookback-days 45
python -m jobs.ingest_market_data --now 2024-01-01T00:00:00 --lookback-days 45
python -m jobs.create_predictions --now 2024-01-01T00:00:00
python -m jobs.resolve_predictions --now 2024-01-02T06:00:00
```

Every job accepts `--now`/`--as-of` so the whole pipeline can be driven
at simulated timestamps without waiting real wall-clock hours.

## Environment variables

See [`.env.example`](.env.example) — every variable is documented inline
and marked `[FREE]`, `[FREE, needs key]` or `[OPTIONAL, PAID]`. The ones
that decide behaviour:

| Variable | Default | Meaning |
|---|---|---|
| `WORLDPULSE_MODE` | `free` | `free` refuses every paid provider and makes `/health` report `"data_mode": "FREE"`. `paid` allows them. |
| `EVENT_PROVIDERS` | `gdelt,usgs,eonet,gdacs` | Comma list of event sources. The default four need no key. |
| `AI_CLASSIFIER` | `rules` | Deterministic rule classifier, no LLM key required. |
| `MARKET_DATA_PROVIDER` | `synthetic` | `binance` / `stooq` / `free` for real free prices; `synthetic` for offline determinism. |
| `DATABASE_URL` | `sqlite:///./worldpulse.db` | SQLite by default; Postgres+pgvector via `docker-compose.yml`. |
| `IMPACT_THRESHOLD` | `0.60` | Minimum impact-candidate score to attempt a prediction. |
| `WORLDMONITOR_API_KEY` | *(unset)* | **Optional, paid.** Leave blank. |

None of these are required to run the tests or the demo.

## What's mocked vs real

Event ingestion is **real** by default: GDELT, USGS, EONET and GDACS are
live public APIs with real HTTP clients, and no key is needed for any of
them. What remains synthetic or rule-based is everything *downstream* of
ingestion, plus the offline demo path — deliberately, so the whole suite
runs deterministically with no network:

| Concern | Default (used everywhere, incl. tests) | Real alternative (pluggable, not wired to default) |
|---|---|---|
| Event sources | **Real, free, keyless**: `GDELTProvider`, `USGSProvider`, `EONETProvider`, `GDACSProvider` (default `EVENT_PROVIDERS`) | `FIRMSProvider` / `ACLEDProvider` add a free registration key; `WorldMonitorProvider` is optional and paid |
| Offline demo event source | `SyntheticEventProvider` (`EVENT_PROVIDERS=synthetic`) -- seeded deterministic timeline, explicitly labelled synthetic | any of the real providers above |
| Market data | `SyntheticMarketDataProvider` -- seeded geometric-random-walk OHLCV (default; deterministic and offline) | **Free, keyless**: `BinancePublicMarketProvider` (real hourly crypto), `StooqMarketProvider` (daily indices/futures/FX/ETFs), or `MARKET_DATA_PROVIDER=free` to chain both with a synthetic fallback. `YFinanceMarketDataProvider` needs the optional `yfinance` package |
| Event extraction | `RuleBasedEventClassifier` (`AI_CLASSIFIER=rules`, the default) -- deterministic keyword rules plus the `config/impact_channels.yaml` event->asset mapping table; **needs no key** | `LLMEventClassifier` -- structured-output call skeleton, requires `OPENAI_API_KEY` / `GROQ_API_KEY` / `OPENROUTER_API_KEY` |
| Prediction explanation | `TemplatedInvestigator` -- templated text over the deterministic statistical output | `LLMInvestigator` -- same prompts (`agents/prompts.py`), requires `OPENAI_API_KEY` |
| Embeddings | Hashing-trick bag-of-words vector (`similarity/embeddings.py`), no network/model download | (not implemented) a real sentence embedding model, or pgvector's ANN index in Postgres |
| Database | SQLite (`sqlite:///./worldpulse.db`), zero external services | Postgres + pgvector, wired via `docker-compose.yml`; the same SQLAlchemy models work against both (see `database/models.py::UTCDateTime` and the comment on the `embedding` column) |

Two smaller, explicitly-documented simplifications (see `docs/LLD.md`
section 4 for detail): analogue matching uses raw returns rather than the
volatility-normalized abnormal returns (`markets/abnormal_returns.py` is
implemented and unit-tested, just not yet wired into the analogue-
matching step), and the scoreboard's baseline comparison uses Baseline A
(always-UP) and a historical-majority stand-in for Baseline C, since
Baseline B (momentum continuation) isn't currently persisted on the
prediction row.

## Repository layout

```
worldpulse/
├── apps/api/main.py            FastAPI app factory
├── apps/dashboard/app.py       Streamlit dashboard (5 pages)
├── src/worldpulse/
│   ├── config.py                Settings (thresholds, DB URL, keys)
│   ├── ingestion/
│   │   ├── providers/            One adapter per event source (base, registry,
│   │   │                         gdelt, usgs, eonet, gdacs, firms, gdacs,
│   │   │                         acled, fred, eia, worldmonitor)
│   │   ├── http_utils.py         Shared retry/backoff/Retry-After HTTP helper
│   │   ├── markets.py            Market data providers (synthetic, Binance, Stooq)
│   │   └── scheduler.py          APScheduler wiring
│   ├── events/                   Schemas, classifier, dedup, entity resolution
│   ├── markets/                  Instruments, returns, abnormal returns
│   ├── similarity/               Embeddings, retrieval, re-ranking
│   ├── prediction/               Features, baselines, model, confidence, predictor
│   ├── evaluation/                Outcome resolver, scoring, calibration
│   ├── agents/                    Investigator + prompts
│   ├── api/                       FastAPI routes
│   └── database/                  SQLAlchemy models + repository
├── config/impact_channels.yaml    Declarative event -> asset/channel mapping
├── scripts/verify_live_providers.py  Live endpoint check (run on your own machine)
├── jobs/                          Standalone pipeline scripts (+ backfill.py)
├── tests/                         pytest suite
└── docs/                          HLD, LLD, UI spec, data-sources.md
```

## A note on this sandbox's filesystem

If you're running this inside a sandbox where the repo directory is a
FUSE/network mount, SQLite's file-based rollback journal can surface as
`disk I/O error` on some mounts that don't support POSIX file locking.
`database/repository.py::make_engine` sets `PRAGMA journal_mode=MEMORY`
on every SQLite connection specifically to work around this. On a normal
local filesystem this has no practical downside for a single-process
dev/demo database.
