# WorldPulse data sources

Every data source WorldPulse can ingest from, with what it costs, how far
back it reaches, how often it updates, and what happens when it is
unavailable.

Two ports, defined in `src/worldpulse/ingestion/providers/base.py`:

- **`WorldEventProvider`** — discrete real-world events → `WorldEvent`.
  Selected via `EVENT_PROVIDERS`.
- **`ContextDataProvider`** — macro/energy *time series* → `SeriesPoint`.
  FRED and EIA only. These deliberately do **not** implement
  `WorldEventProvider`: a weekly inventory print or a daily yield
  observation is a feature, not a newsworthy event, and minting a
  `WorldEvent` per observation would flood the event table and destroy the
  novelty/dedup signals the prediction gate depends on. They cannot appear
  in `EVENT_PROVIDERS`; the registry serves them from
  `get_context_providers()` instead.

Live reachability of the endpoints below is not asserted by the automated
test suite (which is deterministic and fully offline, driving every
adapter through `httpx.MockTransport` with fixture payloads). Verify the
live endpoints yourself with:

```bash
python scripts/verify_live_providers.py --all
```

---

## Cost summary

| Group | Providers |
|---|---|
| **No key of any kind** | GDELT, USGS, EONET, GDACS, Binance (market data), Stooq (market data), synthetic |
| **Free, needs a free registration key** | NASA FIRMS, FRED, EIA, ACLED |
| **Optional, paid** | World Monitor |

`WORLDPULSE_MODE=free` (the default) refuses the paid group outright, even
if it is explicitly listed in `EVENT_PROVIDERS`.

---

## Event providers

### GDELT — `gdelt`

| | |
|---|---|
| **Data provided** | Global news article stream, keyword/phrase searchable, across all five WorldPulse event domains. Per article: title, URL, publisher domain, `seendate`, language, publisher country. |
| **Endpoint** | `https://api.gdeltproject.org/api/v2/doc/doc?query=...&mode=artlist&format=json&maxrecords=...&startdatetime=...&enddatetime=...` |
| **Authentication** | **None.** No key, no registration. |
| **Cost** | Free. |
| **Historical availability** | The DOC 2.0 API reliably serves a **rolling ~3-month window**. Older ranges typically return an empty article list rather than an error — the adapter logs a warning when the requested window starts more than 90 days ago. Deep history (2015→present) requires the GDELT 2.0 Events CSV export (`http://data.gdeltproject.org/gdeltv2/<YYYYMMDDHHMMSS>.export.CSV.zip`, new file every 15 min, index at `masterfilelist.txt`); `gdelt.export_csv_url_for()` builds those URLs, but the bulk loader is **not implemented** in this prototype. |
| **Update frequency** | New content indexed continuously; the 15-minute update cadence of GDELT's underlying pipeline is the practical floor. |
| **Rate limits** | Not formally published. GDELT throttles aggressive clients; `maxrecords` is capped at **250** per request. WorldPulse issues 5 requests per fetch (one per event domain) and defaults `GDELT_MAX_RECORDS=75`. Poll no more often than every few minutes. |
| **How WorldPulse uses it** | The primary source of *geopolitical / conflict / energy / economic* signal, since none of the other free feeds cover those. Because the DOC API is keyword-search based rather than a firehose, the adapter rotates through one curated query per event domain (`DOMAIN_QUERIES` in `providers/gdelt.py`), unions the results, and de-duplicates by article URL. `event_domain` comes from which query matched; `event_subtype` from headline keywords; `occurred_at` from `seendate`; `source_name` from the publisher domain. Severity is a per-domain prior — GDELT supplies no magnitude — refined downstream by the classifier. |
| **Data-quality limits** | (a) `seendate` is when GDELT *saw* the article, not when the event happened — for fast-breaking events these are close, for retrospectives they are not. (b) DOC `mode=artlist` returns **no per-article tone**; sentiment is only reachable through the `tone<`/`tone>` *query operators* (which the conflict/military queries use) or the separate GKG/timeline modes. (c) `sourcecountry` is the *publisher's* country, not the event's, so countries are recovered from headline text instead — imprecise by construction. (d) News volume is a proxy for importance, and it is biased toward English-language and Western coverage. |
| **If unavailable** | The adapter records the failure in `ProviderHealth` and returns `[]`. A single failing domain query is skipped; only an all-queries-failed run is reported as a provider error. Ingestion continues with the remaining providers. |

### USGS earthquakes — `usgs`

| | |
|---|---|
| **Data provided** | Instrumented seismic events: magnitude, magnitude type, epicentre lat/lon, depth, `place`, PAGER alert level, tsunami flag, significance. |
| **Endpoints** | Historical: `https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&starttime=...&endtime=...&minmagnitude=...`. Live: `https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson`. |
| **Authentication** | **None.** |
| **Cost** | Free. |
| **Historical availability** | **The deepest of any provider here.** The ANSS ComCat catalog behind the FDSN service holds significant events back to **1900**, with good global instrumental coverage from the 1960s–70s. Arbitrary historical ranges genuinely work — this is why `jobs/backfill.py --start 2010-01-01 --providers usgs` is a real query. |
| **Update frequency** | The summary feeds regenerate roughly every minute; automatic solutions appear within minutes of an event and are revised (magnitude, depth) over the following hours/days. |
| **Rate limits** | No published quota; USGS asks for reasonable use. FDSN **rejects result sets over 20,000 events** with HTTP 400, so the adapter chunks long backfills into 30-day requests. |
| **How WorldPulse uses it** | `event_domain=natural_disaster`, `event_type/subtype=earthquake`. Severity is magnitude-derived: `(mag − 2.5) / 6.0` clamped to [0,1], with **hard floors at M6 (0.75), M7 (0.88) and M8 (0.97)** because magnitude is logarithmic in energy and a plain linear normalization badly understates large quakes; plus small bumps for a tsunami flag and an orange/red PAGER alert. Lat/lon come from the GeoJSON geometry and are what make the cross-source geo merge work. `provider_event_id` is the USGS event id, so re-ingesting is idempotent. |
| **Data-quality limits** | (a) Early solutions get **revised**; a re-fetch of the same event can carry a different magnitude, and WorldPulse's upsert keeps the first version it saw. (b) `place` is free text, so country attribution is heuristic (US state suffixes → `USA`, otherwise the text after the last comma). (c) Magnitude measures energy release, not economic damage — a M7 in open ocean and a M6 under a semiconductor fab are worlds apart economically but not seismically; the `earthquake + Taiwan → SOXX` impact-channel rule exists precisely to compensate. (d) `USGS_MIN_MAGNITUDE=4.5` by default: smaller quakes are filtered out as market-irrelevant noise. |
| **If unavailable** | Failure recorded, `[]` returned, pipeline continues. |

### NASA EONET — `eonet`

| | |
|---|---|
| **Data provided** | Curated natural-event catalog: wildfires, severe storms, volcanoes, floods, earthquakes, landslides, drought, dust/haze, sea/lake ice, snow, temperature extremes, manmade incidents, water colour. Each event has categories, sources and a geometry track over its lifetime. |
| **Endpoint** | `https://eonet.gsfc.nasa.gov/api/v3/events?status=all&start=YYYY-MM-DD&end=YYYY-MM-DD&limit=N` |
| **Authentication** | **None.** |
| **Cost** | Free. |
| **Historical availability** | Roughly **2000→present** depending on category, dense from ~2015. |
| **Update frequency** | Daily-ish; EONET is curated rather than automated, so entries appear with a lag of hours to days. |
| **Rate limits** | None published; small JSON API. |
| **How WorldPulse uses it** | Maps each EONET category id to an `event_subtype` (`CATEGORY_MAP` in `providers/eonet.py`), with the category id preserved in `event_subtype_detail`. `occurred_at` is the **earliest** geometry observation date (event onset). Polygon geometries are reduced to a ring centroid so the cross-source geo merge always has a point. Where EONET supplies a category-specific magnitude (wildfire acreage, storm wind speed) it nudges the severity prior. |
| **Data-quality limits** | (a) **`status=open` is wrong for backfill** — it returns only still-ongoing events, so this adapter defaults to `status=all`. (b) No country codes at all, only coordinates; `countries` is left empty, which means cross-source matching against a country-only record falls back to the coordinate rule. (c) Curation lag makes EONET unsuitable as a low-latency source. (d) The `manmade` and `waterColor` categories have little market relevance. |
| **If unavailable** | Failure recorded, `[]` returned, pipeline continues. |

### GDACS — `gdacs`

| | |
|---|---|
| **Data provided** | Multi-hazard disaster alerts with an expert-system humanitarian-impact score: earthquake (`EQ`), tropical cyclone (`TC`), flood (`FL`), volcano (`VO`), drought (`DR`), wildfire (`WF`), tsunami (`TS`). Carries `alertlevel` (Green/Orange/Red), `alertscore`, `country`/`iso3`, `fromdate`/`todate`, severity text and a Point geometry. |
| **Endpoint (chosen)** | `https://www.gdacs.org/gdacsapi/api/events/geteventlist/EVENTS4APP` (REST/GeoJSON). |
| **Endpoint (fallback)** | `https://www.gdacs.org/xml/rss.xml` (RSS/XML), implemented in `GDACSProvider._fetch_rss`. |
| **Why the REST API** | It returns `alertlevel`/`alertscore`, hazard code, ISO3 country and typed geometry as structured JSON. The RSS feed buries most of that in prose inside `<description>`. The RSS path is kept as a fallback because it is occasionally reachable when the API host is not, and because it makes no JSON schema assumptions. |
| **Authentication** | **None.** |
| **Cost** | Free. |
| **Historical availability** | **Live/recent only.** `EVENTS4APP` is the *current* alert list (roughly the last few weeks of active events). GDACS hosts per-event historical reports, but there is no documented bulk range query, so a request for an older window returns nothing. **Do not use GDACS for deep backfill** — use USGS. |
| **Update frequency** | Continuous; alert levels are re-evaluated as an event develops (episodes). |
| **Rate limits** | None published. Poll every 15+ minutes. |
| **How WorldPulse uses it** | GDACS's own alert level *is* the severity signal — it already encodes expected humanitarian impact — so severity is taken from it directly (`green→0.35`, `orange→0.70`, `red→0.92`) with `alertscore` spreading values inside the band, rather than being re-derived. This makes GDACS the best severity cross-check for the same physical events USGS and EONET report. |
| **Data-quality limits** | (a) No deep history. (b) Multi-episode events (a cyclone tracked over days) produce several records; `provider_event_id` includes the episode id, so a long-lived event can appear more than once — cross-source dedup collapses them by time+geo. (c) Humanitarian severity ≠ market severity: a red flood alert in a low-income agricultural region scores high on GDACS and low on market impact. |
| **If unavailable** | REST failure falls back to RSS; if both fail the failure is recorded, `[]` returned, pipeline continues. |

### NASA FIRMS — `firms` *(free, needs key)*

| | |
|---|---|
| **Data provided** | Satellite active-fire detections (one row per fire pixel): lat/lon, brightness temperature, FRP (fire radiative power, MW), acquisition date/time, satellite, instrument, confidence, day/night flag. |
| **Endpoint** | `https://firms.modaps.eosdis.nasa.gov/api/area/csv/{MAP_KEY}/{SOURCE}/{west,south,east,north}/{DAY_RANGE}/{DATE}` |
| **Authentication** | A **free MAP_KEY**, instantly issued at <https://firms.modaps.eosdis.nasa.gov/api/>. Set `NASA_FIRMS_API_KEY`. |
| **Cost** | Free (registration only). |
| **Historical availability** | Near-real-time sources (`VIIRS_SNPP_NRT`, `VIIRS_NOAA20_NRT`, `MODIS_NRT`) cover roughly the last 2 months. Standard-processing sources (`MODIS_SP` from **2000**, `VIIRS_SNPP_SP` from **2012**) cover the full archive. |
| **Update frequency** | NRT detections land within ~3 hours of satellite overpass; several overpasses per day per region. |
| **Rate limits** | Documented soft limit of roughly **5000 transactions per 10-minute window per MAP_KEY**, and `DAY_RANGE` is capped at **10 days** — the adapter fetches longer windows as consecutive 10-day chunks. |
| **How WorldPulse uses it** | FIRMS returns *pixels*, not events: one large wildfire is thousands of pixels across many overpasses. Emitting one `WorldEvent` per pixel would swamp the event table and destroy the novelty signal, so `_cluster_detections` performs greedy single-link spatio-temporal clustering (`FIRMS_CLUSTER_RADIUS_KM=50`, `FIRMS_CLUSTER_WINDOW_HOURS=24`) and emits one wildfire-cluster event per cluster with ≥ `FIRMS_MIN_CLUSTER_DETECTIONS` detections. Severity is driven by detection count and total FRP. Cluster ids are derived from a quantized centroid plus start hour, so re-ingesting upserts rather than duplicating. |
| **Data-quality limits** | (a) A `world` query returns hundreds of thousands of pixels per day, so the adapter restricts to six market-relevant bounding boxes (`DEFAULT_AREAS`) — fires outside them are invisible. (b) Cloud cover and overpass timing cause gaps and make detection counts a noisy proxy for fire size. (c) Agricultural burning, gas flares and industrial heat sources register as "fires". (d) Greedy clustering is order-dependent in principle; input is time-sorted, which makes it deterministic in practice. (e) No country attribution, only coordinates and the bounding-box name. |
| **If unavailable / no key** | `is_available()` returns **False**, the registry skips it with a logged reason, and `/health/providers` reports `DISABLED` — **a normal state, not an error**. |

### ACLED — `acled` *(free, needs key; never on by default)*

| | |
|---|---|
| **Data provided** | Hand-coded political violence and protest events: event type / sub-event type, actors, country, admin regions, precise location, lat/lon, fatalities, source, analyst notes. The highest-quality structured conflict dataset available at no cost. |
| **Endpoints** | Token: `POST https://acleddata.com/oauth/token` (`grant_type=password`, `username`, `password`, `client_id=acled`). Read: `GET https://acleddata.com/api/acled/read?_format=json&event_date=<start>|<end>&event_date_where=BETWEEN&limit=&page=` with `Authorization: Bearer <token>`. |
| **Authentication** | **Free registration** at <https://acleddata.com/register/>, then the OAuth password grant above. Requires **both** `ACLED_EMAIL` and `ACLED_PASSWORD`. |
| **Cost** | Free for academic/non-commercial use under ACLED's terms; commercial use requires a licence. **Check ACLED's terms of use before deploying commercially.** |
| **Historical availability** | 1997→present for Africa, 2010→present for Asia, **global coverage from 2018**. |
| **Update frequency** | Weekly (Tuesdays), with roughly a **one-week reporting lag**. This makes ACLED a research/backfill source, not a low-latency one. |
| **Rate limits** | The free tier is capped at a limited number of API calls and rows per month. The adapter pages with `limit`/`page` (500 rows/page, max 10 pages per fetch) and caches its OAuth token until 60s before expiry. |
| **How WorldPulse uses it** | Maps ACLED `event_type` onto WorldPulse domains (`Battles→military_activity/armed_clash`, `Explosions/Remote violence→military_activity/missile_strike`, `Protests`/`Riots`/`Violence against civilians`→`conflict_geopolitical`). ACLED supplies no severity field, so severity is a saturating function of fatalities (`0.30 + min(0.60, fatalities/200 × 0.60)`). |
| **Data-quality limits** | (a) The weekly lag makes it useless for live prediction — it is for building a historical analogue base. (b) Fatalities is a crude severity proxy and is itself often uncertain or disputed. (c) One real-world escalation is often coded as many discrete events. (d) The OAuth flow changed in 2024; if ACLED revises it again this adapter needs updating. |
| **If unavailable / no key** | `is_available()` returns **False**, skipped with a logged reason, reported `DISABLED`. **Not in the default `EVENT_PROVIDERS`.** |

### World Monitor — `worldmonitor` *(optional, PAID)*

| | |
|---|---|
| **Data provided** | Curated news/intel stream with source-assigned category and severity hints plus a corroboration count. |
| **Authentication** | `WORLDMONITOR_API_KEY` + the `worldmonitor-sdk` package. |
| **Cost** | **Paid subscription.** |
| **Historical availability** | Per the vendor. |
| **Update frequency** | Per the vendor. |
| **Rate limits** | Per the vendor. |
| **How WorldPulse uses it** | Wrapped as one provider among many in `providers/worldmonitor.py`. Its raw items go through the existing `RuleBasedEventClassifier.classify(RawNewsItem)` path unchanged. |
| **Status in this build** | **Fully optional.** It is not in the default `EVENT_PROVIDERS`; with `WORLDPULSE_MODE=free` (the default) it is refused even when explicitly listed; and with the key absent `is_available()` returns False and the registry logs `WorldMonitorProvider disabled: WORLDMONITOR_API_KEY not set`. The SDK integration itself remains a skeleton (`WorldMonitorSDKClient` raises `NotImplementedError` on fetch) — it was never wired up in this prototype. Regression coverage: `tests/test_no_worldmonitor_required.py`. |
| **If unavailable / no key** | Skipped; reported `DISABLED`. Nothing downstream changes. |

### Synthetic — `synthetic` *(free, offline)*

| | |
|---|---|
| **Data provided** | A seeded, deterministic synthetic event timeline (4000 items over 2020-01-01 + 10 years) spanning all five domains. |
| **Authentication / cost** | None / free. No network access at all. |
| **Historical availability** | 2020-01-01 → 2029-12-31 (the fixed generator span). |
| **How WorldPulse uses it** | The offline demo and test event source, and the analogue-history seed in the walk-forward backfill. |
| **Data-quality limits** | **It is synthetic.** Headlines are template-generated and severities are drawn from per-scenario uniform ranges; nothing here reflects real-world frequencies or real market reactions. It is labelled `provider="synthetic"` on every record precisely so it can never be mistaken for a real feed. It is a *correctness* fixture, not a data source. |

---

## Context / feature providers (NOT event sources)

### FRED — `fred` *(free, needs key)*

| | |
|---|---|
| **Data provided** | Macro time series: policy rates, treasury yields and spreads, CPI, dollar index, Brent spot. |
| **Endpoint** | `https://api.stlouisfed.org/fred/series/observations?series_id=...&api_key=...&file_type=json&observation_start=...&observation_end=...` |
| **Authentication** | **Free** key from <https://fredaccount.stlouisfed.org/apikeys>. Set `FRED_API_KEY`. |
| **Cost** | Free. |
| **Historical availability** | Full series history — many series reach back decades (`DGS10` to 1962). |
| **Update frequency** | Per series: daily for yields, monthly for CPI. |
| **Rate limits** | **120 requests/minute** per API key. |
| **How WorldPulse uses it** | `get_series()` returns normalized `SeriesPoint`s for the feature layer. **It does not implement `WorldEventProvider`** and cannot be listed in `EVENT_PROVIDERS`. |
| **Data-quality limits** | Series are **revised** — the value FRED reports today for a past date is not necessarily what was known then. Using latest-vintage data as a point-in-time feature is a look-ahead bias; FRED's ALFRED vintages solve this and are **not** used here. Missing observations arrive as the string `"."` and are mapped to `None` (kept, not dropped, so gaps stay visible). |
| **If unavailable / no key** | `is_available()` False; `get_series()` returns `[]`. The feature layer simply runs without macro context. |

### EIA — `eia` *(free, needs key)*

| | |
|---|---|
| **Data provided** | Energy time series: crude stocks (ex-SPR), WTI/Brent spot, refinery net input, Henry Hub gas. |
| **Endpoint** | `https://api.eia.gov/v2/seriesid/{SERIES_ID}?api_key=...&start=...&end=...` (the API v2 legacy-series compatibility route; the fully-general `/v2/<route>/data/` form is also real but needs a per-dataset route + facet vocabulary). |
| **Authentication** | **Free** key from <https://www.eia.gov/opendata/>. Set `EIA_API_KEY`. |
| **Cost** | Free. |
| **Historical availability** | Full series history; weekly petroleum series reach back to the 1980s. |
| **Update frequency** | Weekly (Wednesdays) for petroleum stocks; daily for spot prices. |
| **Rate limits** | A per-key hourly limit (order of a few thousand requests); the API returns HTTP 429, which the shared retry helper honours via `Retry-After`. |
| **How WorldPulse uses it** | Energy context for the `energy_supply` impact channel. **Not an event source**, same rationale as FRED. |
| **Data-quality limits** | Weekly cadence and revisions; `period` granularity varies by series frequency, so timestamps are parsed against several formats. Reported figures are estimates subject to later correction. |
| **If unavailable / no key** | `is_available()` False; `get_series()` returns `[]`. |

---

## Market data providers

The `MarketDataProvider` port is unchanged by this refactor, so the
prediction and evaluation layers are agnostic to which of these is in use.

### Synthetic *(default)*

Seeded geometric-random-walk OHLCV, volatility-calibrated per asset class.
Deterministic, offline, free. Generated forward from a fixed epoch so
overlapping windows always agree bar-for-bar — required by the
no-look-ahead tests. **Not real prices**; use it for pipeline correctness,
never for a claim about real market behaviour.

### Binance public klines — `binance` *(free, no auth)*

| | |
|---|---|
| **Endpoint** | `https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&startTime=<ms>&endTime=<ms>&limit=1000` |
| **Authentication** | **None.** |
| **Coverage** | Crypto spot only (`BTC-USD→BTCUSDT`, `ETH-USD→ETHUSDT`), full history from each pair's listing (BTCUSDT from 2017-08), real **hourly** granularity — the only free source here that can actually evaluate WorldPulse's 1h/4h/8h/12h horizons. |
| **Rate limits** | Weighted IP budget (6000 request-weight/minute; a klines call costs 1–2). HTTP 429 with `Retry-After` when exceeded, HTTP 418 on a ban. Responses cap at **1000 candles**, so the adapter pages. |
| **Limits** | Crypto only. Binance is geo-restricted in some jurisdictions; from a blocked IP requests fail and the adapter degrades to `[]` (then to the next provider in the composite). |

### Stooq daily CSV — `stooq` *(free, no auth)*

| | |
|---|---|
| **Endpoint** | `https://stooq.com/q/d/l/?s=<ticker>&i=d&d1=YYYYMMDD&d2=YYYYMMDD` |
| **Authentication** | **None.** |
| **Coverage** | Multi-decade **daily** history for equity indices (`^spx`, `^ndq`, `^vix`), continuous futures (`gc.f`, `cl.f`, `cb.f`, `ng.f`, `hg.f`, `dx.f`), FX pairs and US ETFs (`soxx.us`, `xle.us`, `ita.us`, `tlt.us`). |
| **Rate limits** | Undocumented; Stooq throttles aggressive scraping. Fetch a few symbols at a time and cache. |
| **Limits** | **Daily bars only** — the CSV endpoint has no intraday interval, so WorldPulse's 1h/4h/8h/12h horizons **cannot be evaluated from Stooq data**. Requesting a sub-daily interval logs a warning and returns daily bars. Continuous-futures series also carry roll artifacts. |

### `yfinance` — `yfinance` *(optional package)*

Requires the optional `yfinance` dependency; unofficial and rate-limited,
guarded so a missing package or network failure degrades to `[]`. Never
used by default.

### Composite — `free`

`MARKET_DATA_PROVIDER=free` chains Binance (crypto) → Stooq (everything
else it covers) → synthetic (the remainder), so a fully free deployment
gets real prices where they exist and a deterministic fallback where they
do not. **The fallback is silent to callers** — check `Bar.source` to see
which provider actually answered.

---

## Failure and degradation policy

Uniform across all providers:

1. **Missing optional credential** → `is_available()` False → the registry
   skips the provider with a logged reason → `/health/providers` reports
   `DISABLED`. This is a normal state; the endpoint still returns HTTP 200.
2. **Transient HTTP failure** → `ingestion/http_utils.py` retries with
   exponential backoff, honouring `Retry-After`; a non-retryable 4xx fails
   fast.
3. **Exhausted retries or a bad payload** → the provider records the error
   in `ProviderHealth` (status `DEGRADED`) and returns `[]`. **It never
   raises into the pipeline** — one broken feed cannot take ingestion down.
4. **No active providers at all** → ingestion logs a warning and is a
   no-op. It does not crash.

Health for every provider, including unselected and disabled ones:

```bash
curl localhost:8000/health/providers
```
