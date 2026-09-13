# WorldPulse -- Dashboard UI Spec

Implemented as a single Streamlit app (`apps/dashboard/app.py`) with a
sidebar page selector for 5 screens, plus a "Run demo pipeline" control
that drives the full ingest -> predict -> resolve loop at simulated
timestamps so a viewer can see results without waiting real hours.

All screens read from the same SQLite database (via
`worldpulse.database.repository`) that the API and jobs use.

## Sidebar (always visible)

- Page selector (radio): World Pulse / Event Investigator / Prediction
  Board / Prediction Replay / Scoreboard.
- "Demo pipeline: simulated days" slider (5-60).
- "Run demo pipeline" button: calls, per simulated day,
  `jobs.ingest_world_events.main` -> `jobs.ingest_market_data.main` ->
  `jobs.create_predictions.main` -> `jobs.resolve_predictions.main`, then
  a final resolution pass past the longest horizon.

## 1. World Pulse -- live event feed

**Shows:** the most recent 50 classified events as cards, each with
headline, event type/subtype, occurred_at, severity (as a metric), and
countries involved.

**Sample data:** "Russia masses troops near Ukraine border" /
military_activity/troop_movement / severity 0.82 / Russia, Ukraine.

**API equivalent:** `GET /events?limit=50`.

## 2. Event Investigator -- event detail + analogues + AI explanation

**Shows:** a dropdown of events; for the selected event: headline, type,
countries, severity; a table of the top-10 historical analogues (ranked
by the similarity re-rank score) with their headline/date/similarity; and
one expander per prediction generated for that event, each showing the
`TemplatedInvestigator` explanation (observed facts, historical
association, AI hypothesis clearly labeled as a hypothesis, plain-
language prediction restatement, and what would invalidate it).

**API equivalent:** `GET /events/{id}`, `GET /events/{id}/similar`, the
predictions for the event (would be a filtered `GET /predictions`), and
`GET /events/{id}/impact` for the gating score.

## 3. Prediction Board -- live predictions

**Shows:** all unresolved (not-yet-resolved) predictions, grouped into a
subheader per horizon (+1h, +4h, +8h, +12h, +24h), each a table of
symbol / signal / probability / sample_size / confidence tier. A
`NO_PREDICTION` row renders as `"No reliable signal"` in the signal
column with a blank probability, rather than a directional call.

**API equivalent:** `GET /predictions/live`.

## 4. Prediction Replay -- price timeline around an event

**Shows:** a dropdown of predictions; for the selected one, a line chart
of the symbol's price from T-24h to T+24h around the event (via
`st.line_chart`), the event headline/time as a caption, the prediction's
direction/probability, and -- once resolved -- the actual realized return
and correct/incorrect result.

**API equivalent:** `GET /predictions/{id}`, plus bar data (not yet a
dedicated endpoint; the dashboard calls `SyntheticMarketDataProvider`
directly for the same deterministic bars the pipeline used).

## 5. Scoreboard -- aggregate performance

**Shows:** four top-line metrics (total predictions, total resolved,
coverage, directional accuracy), then tables for precision by confidence
tier, accuracy by horizon, accuracy by event domain, baseline comparison
(always-UP and historical-unconditional), and the calibration table
(predicted-probability bucket vs. realized accuracy).

**API equivalent:** `GET /performance`, `GET /performance/horizons`,
`GET /performance/categories`.

## Running it

```bash
streamlit run apps/dashboard/app.py
```

On first launch, every screen will say "no data yet" until you click
**Run demo pipeline** in the sidebar (or run `python jobs/backfill.py`
separately against the same `DATABASE_URL`).
