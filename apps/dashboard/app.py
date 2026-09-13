"""WorldPulse Streamlit dashboard.

Run with: streamlit run apps/dashboard/app.py

Five pages/tabs: World Pulse (live feed), Event Investigator, Prediction
Board, Prediction Replay, Scoreboard. A "Run demo pipeline" button in the
sidebar drives jobs/ingest_world_events -> create_predictions ->
resolve_predictions at accelerated simulated timestamps so the full loop
is visible without waiting real wall-clock hours.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

# Ensure the repo's src/ and repo root are importable when run directly by
# `streamlit run apps/dashboard/app.py` from the repo root.
REPO_ROOT = Path(__file__).resolve().parents[2]
for p in (str(REPO_ROOT / "src"), str(REPO_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from sqlalchemy import select  # noqa: E402

from worldpulse.agents.investigator import TemplatedInvestigator  # noqa: E402
from worldpulse.database.models import PredictionORM, WorldEventORM  # noqa: E402
from worldpulse.database.repository import (  # noqa: E402
    _orm_to_event, get_bars_as_of, get_default_session_factory, get_events_as_of,
)
from worldpulse.evaluation.calibration import compute_calibration_table  # noqa: E402
from worldpulse.evaluation.scoring import compute_scoreboard  # noqa: E402
from worldpulse.ingestion.markets import SyntheticMarketDataProvider  # noqa: E402
from worldpulse.prediction.predictor import PredictionResult  # noqa: E402
from worldpulse.similarity.retrieval import retrieve_analogues  # noqa: E402
from worldpulse.similarity.ranking import rerank  # noqa: E402

st.set_page_config(page_title="WorldPulse", layout="wide")


@st.cache_resource
def get_session_factory():
    return get_default_session_factory()


def get_session():
    return get_session_factory()()


def run_demo_pipeline(days: int = 10, seed: int = 42):
    import jobs.create_predictions as create_predictions
    import jobs.ingest_market_data as ingest_market_data
    import jobs.ingest_world_events as ingest_world_events
    import jobs.resolve_predictions as resolve_predictions

    # Anchor the simulated walk-forward window to the system clock so a
    # fresh run always shows current-looking dates, rather than a fixed
    # historical date. The window runs from (now - days) up to now.
    start = datetime.now(timezone.utc) - timedelta(days=days)
    progress = st.progress(0, text="Starting demo pipeline...")
    for i in range(days):
        as_of = start + timedelta(days=i)
        ingest_world_events.main(now=as_of, lookback_days=45, seed=seed)
        ingest_market_data.main(now=as_of, lookback_days=45, seed=seed)
        create_predictions.main(now=as_of, seed=seed, lookback_days=45)
        resolve_predictions.main(now=as_of, seed=seed)
        progress.progress((i + 1) / days, text=f"Simulated day {i + 1}/{days}")
    resolve_predictions.main(now=start + timedelta(days=days + 3), seed=seed)
    progress.progress(1.0, text="Done")
    st.success(f"Demo pipeline complete: simulated {days} days.")


st.sidebar.title("WorldPulse")
page = st.sidebar.radio(
    "Page",
    ["World Pulse", "Event Investigator", "Prediction Board", "Prediction Replay", "Scoreboard"],
)
st.sidebar.markdown("---")
demo_days = st.sidebar.slider("Demo pipeline: simulated days", 5, 60, 10)
if st.sidebar.button("Run demo pipeline"):
    with st.spinner("Running full ingest -> predict -> resolve loop..."):
        run_demo_pipeline(days=demo_days)
    st.cache_resource.clear()

session = get_session()


def _event_rows(limit: int = 50) -> list[WorldEventORM]:
    stmt = select(WorldEventORM).order_by(WorldEventORM.occurred_at.desc()).limit(limit)
    return list(session.execute(stmt).scalars().all())


def _prediction_rows(limit: int = 200) -> list[PredictionORM]:
    stmt = select(PredictionORM).order_by(PredictionORM.created_at.desc()).limit(limit)
    return list(session.execute(stmt).scalars().all())


if page == "World Pulse":
    st.header("World Pulse -- Live Event Feed")
    st.caption("Most recent classified world events (synthetic feed).")
    rows = _event_rows(50)
    if not rows:
        st.info("No events yet. Use 'Run demo pipeline' in the sidebar to generate data.")
    for row in rows:
        with st.container(border=True):
            cols = st.columns([3, 1, 1])
            cols[0].markdown(f"**{row.headline}**")
            cols[0].caption(f"{row.event_type} / {row.event_subtype} | {row.occurred_at}")
            cols[1].metric("Severity", f"{row.severity:.2f}")
            cols[2].write(f"Countries: {', '.join(json.loads(row.countries))}")

elif page == "Event Investigator":
    st.header("Event Investigator")
    rows = _event_rows(200)
    if not rows:
        st.info("No events yet. Use 'Run demo pipeline' in the sidebar to generate data.")
    else:
        options = {f"{r.occurred_at} | {r.headline}": r.id for r in rows}
        selected_label = st.selectbox("Select an event", list(options.keys()))
        event_id = options[selected_label]
        row = session.get(WorldEventORM, event_id)
        target = _orm_to_event(row)

        st.subheader(target.headline)
        st.write(f"Type: {target.event_type} / {target.event_subtype}")
        st.write(f"Countries: {', '.join(target.countries)} | Severity: {target.severity:.2f}")

        st.markdown("### Historical analogues")
        candidates = [e for e in get_events_as_of(session, as_of=target.occurred_at) if e.id != target.id]
        reranked = rerank(target, retrieve_analogues(target, candidates, top_k=10))
        if reranked:
            df = pd.DataFrame([
                {"headline": c.headline, "occurred_at": c.occurred_at, "similarity": round(s, 3)}
                for c, s in reranked
            ])
            st.dataframe(df, use_container_width=True)
        else:
            st.write("No historical analogues found.")

        st.markdown("### Predictions for this event")
        preds = list(session.execute(
            select(PredictionORM).where(PredictionORM.event_id == event_id)
        ).scalars().all())
        if preds:
            for p in preds:
                with st.expander(f"{p.symbol} @ +{p.horizon_hours}h -> {p.direction} ({p.confidence_tier})"):
                    st.write(f"Probability: {p.probability:.0%}, sample_size={p.sample_size}")
                    result = PredictionResult(
                        event_id=p.event_id, symbol=p.symbol, horizon_hours=p.horizon_hours,
                        direction=p.direction, probability=p.probability, expected_return=p.expected_return,
                        median_return=p.median_return, p25_return=p.p25_return, p75_return=p.p75_return,
                        sample_size=p.sample_size, confidence_tier=p.confidence_tier,
                        event_domain=p.event_domain, created_at=p.created_at,
                        explanation=json.loads(p.explanation_json) if p.explanation_json else {},
                    )
                    explanation = TemplatedInvestigator().explain(target, result)
                    st.markdown("**Observed facts**")
                    st.write(explanation.observed_facts)
                    st.markdown("**Historical association**")
                    st.write(explanation.historical_association)
                    st.markdown("**AI hypothesis**")
                    st.write(explanation.ai_hypothesis)
                    st.markdown("**Prediction**")
                    st.write(explanation.prediction)
                    st.markdown("**What would invalidate this**")
                    st.write(explanation.what_would_invalidate)
        else:
            st.write("No predictions were generated for this event (likely below the impact-score gate).")

elif page == "Prediction Board":
    st.header("Prediction Board -- Live Predictions")
    preds = _prediction_rows(300)
    unresolved = [p for p in preds if p.resolved_at is None]
    if not unresolved:
        st.info("No live predictions yet. Use 'Run demo pipeline' in the sidebar.")
    else:
        by_horizon: dict[int, list[PredictionORM]] = {}
        for p in unresolved:
            by_horizon.setdefault(p.horizon_hours, []).append(p)
        for horizon in sorted(by_horizon):
            st.subheader(f"+{horizon}h horizon")
            rows = []
            for p in by_horizon[horizon]:
                if p.direction == "NO_PREDICTION":
                    rows.append({"symbol": p.symbol, "signal": "No reliable signal",
                                 "probability": None, "sample_size": p.sample_size, "tier": p.confidence_tier})
                else:
                    rows.append({"symbol": p.symbol, "signal": p.direction,
                                 "probability": p.probability, "sample_size": p.sample_size, "tier": p.confidence_tier})
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

elif page == "Prediction Replay":
    st.header("Prediction Replay")
    preds = _prediction_rows(300)
    if not preds:
        st.info("No predictions yet. Use 'Run demo pipeline' in the sidebar.")
    else:
        options = {f"{p.created_at} | {p.symbol} +{p.horizon_hours}h ({p.direction})": p.id for p in preds}
        selected_label = st.selectbox("Select a prediction", list(options.keys()))
        prediction_id = options[selected_label]
        p = session.get(PredictionORM, prediction_id)
        event_row = session.get(WorldEventORM, p.event_id)
        event = _orm_to_event(event_row)

        provider = SyntheticMarketDataProvider()
        window_start = event.occurred_at - timedelta(hours=24)
        window_end = event.occurred_at + timedelta(hours=24)
        bars = provider.get_bars(p.symbol, window_start, window_end, interval="1h")
        if bars:
            df = pd.DataFrame([{"timestamp": b.timestamp, "close": b.close} for b in bars]).set_index("timestamp")
            st.line_chart(df)
        st.write(f"Event at T=0: {event.headline} (occurred {event.occurred_at})")
        st.write(f"Prediction: {p.direction} @ +{p.horizon_hours}h, probability={p.probability:.0%}")
        if p.resolved_at:
            st.write(f"Actual return: {p.actual_return:.3%} -- {p.result}")
        else:
            st.write("Not yet resolved.")

elif page == "Scoreboard":
    st.header("Scoreboard")
    preds = list(session.execute(select(PredictionORM)).scalars().all())
    if not preds:
        st.info("No predictions yet. Use 'Run demo pipeline' in the sidebar.")
    else:
        report = compute_scoreboard(preds)
        cols = st.columns(4)
        cols[0].metric("Total predictions", report.total_predictions)
        cols[1].metric("Total resolved", report.total_resolved)
        cols[2].metric("Coverage", f"{report.coverage:.1%}")
        cols[3].metric("Directional accuracy",
                        f"{report.directional_accuracy:.1%}" if report.directional_accuracy is not None else "n/a")

        st.subheader("Precision by confidence tier")
        st.table(pd.DataFrame([{"tier": k, "accuracy": v} for k, v in report.precision_by_tier.items()]))

        st.subheader("Accuracy by horizon")
        st.table(pd.DataFrame([{"horizon_hours": k, "accuracy": v} for k, v in report.accuracy_by_horizon.items()]))

        st.subheader("Accuracy by event domain")
        st.table(pd.DataFrame([{"domain": k, "accuracy": v} for k, v in report.accuracy_by_domain.items()]))

        st.subheader("vs. Baselines")
        st.table(pd.DataFrame([{"baseline": k, "accuracy": v} for k, v in report.baseline_accuracy.items()]))

        st.subheader("Calibration table")
        calib = compute_calibration_table(preds)
        st.table(pd.DataFrame([
            {"bucket": f"{b.bucket_low:.0%}-{b.bucket_high:.0%}", "n": b.n,
             "mean_predicted_probability": round(b.mean_predicted_probability, 3),
             "realized_accuracy": round(b.realized_accuracy, 3)}
            for b in calib
        ]))
