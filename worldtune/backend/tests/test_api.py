"""API endpoints via FastAPI's TestClient, plus the end-to-end dashboard test."""
from __future__ import annotations

import pytest

from app.api.security import RateLimiter, clamp_limit, sanitize_query


class TestSystem:
    def test_health(self, client):
        body = client.get("/health").json()
        assert body["status"] == "ok"
        assert body["demo_mode"] is True

    def test_data_sources_reports_demo_vs_live(self, client):
        body = client.get("/api/system/data-sources").json()
        assert body["demo_mode"] is True
        assert set(body["selected"]) == {"market", "news", "jobs", "technology"}
        # In demo mode every selected provider must be a demo adapter.
        for names in body["selected"].values():
            assert all(n.startswith("demo:") for n in names)
        # ...but the live adapters are still *reported*, with their key status.
        names = {p["name"] for p in body["providers"]}
        assert {"coingecko", "stooq", "gdelt", "remoteok", "adzuna",
                "github", "hackernews"} <= names
        adzuna = next(p for p in body["providers"] if p["name"] == "adzuna")
        assert adzuna["available"] is False        # no credentials configured
        assert adzuna["requires_credentials"] == ["ADZUNA_APP_ID", "ADZUNA_APP_KEY"]

    def test_stats_carries_the_disclaimer(self, client):
        body = client.get("/api/system/stats").json()
        assert "profitability" in body["disclaimer"].lower()
        assert body["counts"]["jobs"] > 0


class TestPersona:
    def test_get_returns_the_seeded_demo_persona(self, client):
        persona = client.get("/api/persona").json()
        assert persona["career"]["current_role"] == "Senior Data Engineer"
        assert persona["career"]["years_experience"] == 10
        assert persona["location"]["city"] == "Bengaluru"
        assert persona["financial"]["watchlist"] == ["BTC", "ETH"]
        assert "Staff Data Engineer" in persona["career"]["target_roles"]
        assert "AI engineering" in persona["preferences"]["learning_topics"]
        assert persona["id"]

    def test_put_updates_and_persists(self, client):
        persona = client.get("/api/persona").json()
        persona["career"]["current_role"] = "Staff Data Engineer"
        persona["financial"]["watchlist"] = ["BTC", "ETH", "SOL"]

        updated = client.put("/api/persona", json=persona)
        assert updated.status_code == 200
        assert updated.json()["career"]["current_role"] == "Staff Data Engineer"

        assert client.get("/api/persona").json()["financial"]["watchlist"] == \
            ["BTC", "ETH", "SOL"]

    def test_put_rejects_an_invalid_payload(self, client):
        assert client.put("/api/persona", json={"financial": {"risk_appetite": "reckless"}}) \
            .status_code == 422

    def test_persona_change_changes_the_ranking(self, client):
        """Personalization must actually be driven by the persona."""
        before = client.get("/api/financial/pulse").json()["entries"]
        before_score = {e["entity_id"]: e["worldtune_score"] for e in before}

        persona = client.get("/api/persona").json()
        persona["financial"]["watchlist"] = ["NVDA"]
        persona["financial"]["sectors"] = ["AI"]
        client.put("/api/persona", json=persona)

        after = client.get("/api/financial/pulse").json()["entries"]
        after_score = {e["entity_id"]: e["worldtune_score"] for e in after}
        assert after_score.get("NVDA", 0) > before_score.get("NVDA", 0)


class TestFinancial:
    def test_pulse_entries_are_explained_and_ranked(self, client):
        body = client.get("/api/financial/pulse?limit=5").json()
        entries = body["entries"]
        assert entries
        assert [e["worldtune_score"] for e in entries] == \
            sorted([e["worldtune_score"] for e in entries], reverse=True)
        for entry in entries:
            assert 0 <= entry["worldtune_score"] <= 100
            assert set(entry["score_breakdown"]["components"]) >= {
                "persona_relevance", "trend_momentum", "evidence_strength",
                "novelty", "recency", "prediction_confidence"}
            assert entry["evidence"]
            assert entry["trajectory"]["direction"] in {"bullish", "neutral", "bearish"}
            assert entry["explanation"]["summary"]

    def test_trajectory_never_contains_a_price_target(self, client):
        for entry in client.get("/api/financial/pulse").json()["entries"]:
            assert "predicted_price" not in entry["trajectory"]
            assert "price_target" not in entry["trajectory"]

    def test_asset_detail(self, client):
        body = client.get("/api/financial/assets/BTC").json()
        assert body["entity_id"] == "BTC"
        assert body["metrics"]["n_price_observations"] > 30

    def test_unknown_asset_is_404(self, client):
        assert client.get("/api/financial/assets/NOPE").status_code == 404


class TestCareer:
    def test_pulse_has_skills_and_jobs(self, client):
        body = client.get("/api/career/pulse?limit=5").json()
        assert body["skill_signals"] and body["job_matches"]
        for signal in body["skill_signals"]:
            assert signal["metrics"]["direction"] in {"growing", "stable", "declining"}
            assert set(signal["trajectory_by_horizon"]) == {"7d", "30d", "90d"}
            assert signal["explanation"]["recommended_action"]

    def test_skill_scope_filtering(self, client):
        body = client.get("/api/career/skills?scope_type=location&scope_value=Bengaluru").json()
        assert body["scope"]["value"] == "Bengaluru"
        assert body["entries"]

    def test_skill_detail(self, client):
        skill_id = client.get("/api/career/skills?limit=1").json()["entries"][0]["entity_id"]
        assert client.get(f"/api/career/skills/{skill_id}").json()["entity_id"] == skill_id

    def test_unknown_skill_is_404(self, client):
        assert client.get("/api/career/skills/notaskill").status_code == 404

    def test_jobs_carry_matched_skills_and_a_breakdown(self, client):
        for job in client.get("/api/career/jobs?limit=5").json()["entries"]:
            assert job["score_breakdown"]["components"]
            assert "matched_skills" in job


class TestOtherEndpoints:
    def test_technology_signals(self, client):
        body = client.get("/api/technology/signals").json()
        assert body["count"] > 0
        assert "related_skills" in body["entries"][0]

    def test_news(self, client):
        assert client.get("/api/news?days=60").json()["count"] > 0

    def test_news_query_filter(self, client):
        body = client.get("/api/news?days=60&q=bitcoin").json()
        assert all("bitcoin" in e["title"].lower() for e in body["entries"])

    def test_generic_signal_spine(self, client):
        body = client.get("/api/signals?limit=10").json()
        assert body["entries"]
        kinds = {e["signal_type"] for e in client.get("/api/signals?limit=100").json()["entries"]}
        assert kinds & {"news", "job", "technology"}

    def test_daily_tune_has_actionable_kinds(self, client):
        body = client.get("/api/daily-tune").json()
        kinds = {item["kind"] for item in body["items"]}
        assert kinds <= {"learn", "apply", "watch", "read"}
        assert len(kinds) >= 3
        for item in body["items"]:
            assert item["title"] and item["why"]

    def test_daily_tune_persist_and_history(self, client):
        assert client.get("/api/daily-tune?persist=true").json()["count"] > 0
        assert client.get("/api/daily-tune/history").json()["count"] > 0

    def test_predictions_list(self, client):
        body = client.get("/api/predictions?limit=5").json()
        assert body["entries"]
        assert "profitability" in body["disclaimer"].lower()

    def test_prediction_accuracy_reports_real_metrics(self, client):
        body = client.get("/api/predictions/accuracy?domain=financial").json()
        assert body["n"] > 0
        assert 0.0 <= body["accuracy"] <= 1.0
        assert body["calibration"]
        assert "profitability" in body["disclaimer"].lower()

    def test_accuracy_with_no_data_says_so(self, client):
        body = client.get("/api/predictions/accuracy?domain=career").json()
        assert body["n"] == 0 and "message" in body


class TestSecurity:
    def test_sanitize_strips_injection_characters(self):
        # Apostrophes survive (they appear in legitimate company names); the
        # statement separator is what gets neutralized.
        assert sanitize_query("spark'; DROP TABLE jobs;--") == "spark' DROP TABLE jobs --"
        assert ";" not in sanitize_query("a; b")
        assert "<" not in sanitize_query("<script>alert(1)</script>")

    def test_sanitize_preserves_legitimate_query_text(self):
        assert sanitize_query("C++ / data-engineering & AI") == "C++ / data-engineering & AI"

    def test_sanitize_rejects_overlong_input(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            sanitize_query("a" * 500)

    def test_sanitize_handles_none(self):
        assert sanitize_query(None) == ""

    def test_overlong_query_is_422_at_the_api(self, client):
        assert client.get("/api/news?q=" + "a" * 500).status_code == 422

    def test_clamp_limit(self):
        assert clamp_limit(None, default=7) == 7
        assert clamp_limit(9999, maximum=100) == 100
        assert clamp_limit(-5) == 1

    def test_rate_limiter_blocks_past_the_limit(self):
        limiter = RateLimiter(limit=3, window_seconds=60)
        assert all(limiter.check("ip", now=0.0)[0] for _ in range(3))
        allowed, retry_after = limiter.check("ip", now=0.0)
        assert allowed is False and retry_after > 0

    def test_rate_limiter_window_slides(self):
        limiter = RateLimiter(limit=1, window_seconds=10)
        assert limiter.check("ip", now=0.0)[0] is True
        assert limiter.check("ip", now=5.0)[0] is False
        assert limiter.check("ip", now=11.0)[0] is True

    def test_rate_limiter_is_per_client(self):
        limiter = RateLimiter(limit=1, window_seconds=60)
        assert limiter.check("a", now=0.0)[0] is True
        assert limiter.check("b", now=0.0)[0] is True


class TestEndToEnd:
    """Seed demo data -> GET /api/dashboard -> assert the whole product works."""

    def test_dashboard_matches_the_spec_shape(self, client):
        body = client.get("/api/dashboard").json()
        assert set(body) >= {"persona", "summary", "financial_pulse",
                             "career_pulse", "daily_tune", "generated_at"}

    def test_dashboard_persona_is_present_and_correct(self, client):
        persona = client.get("/api/dashboard").json()["persona"]
        assert persona["career"]["current_role"] == "Senior Data Engineer"
        assert persona["location"]["city"] == "Bengaluru"

    def test_financial_pulse_entries_have_a_full_score_breakdown(self, client):
        entries = client.get("/api/dashboard").json()["financial_pulse"]
        assert entries
        for entry in entries:
            breakdown = entry["score_breakdown"]
            assert set(breakdown["components"]) == {
                "persona_relevance", "trend_momentum", "evidence_strength",
                "novelty", "recency", "prediction_confidence"}
            total = sum(c["contribution"] for c in breakdown["components"].values())
            assert total == pytest.approx(entry["worldtune_score"], abs=0.05)
            assert breakdown["evidence"]

    def test_career_pulse_entries_have_a_full_score_breakdown(self, client):
        career = client.get("/api/dashboard").json()["career_pulse"]
        assert career["skill_signals"] and career["job_matches"]
        for entry in career["skill_signals"] + career["job_matches"]:
            assert set(entry["score_breakdown"]["components"]) == {
                "persona_relevance", "trend_momentum", "evidence_strength",
                "novelty", "recency", "prediction_confidence"}
            assert 0 <= entry["worldtune_score"] <= 100

    def test_daily_tune_has_learn_apply_watch_read_entries(self, client):
        items = client.get("/api/dashboard").json()["daily_tune"]
        kinds = {i["kind"] for i in items}
        assert kinds <= {"learn", "apply", "watch", "read"}
        assert len(kinds) >= 3, f"expected a diverse Daily Tune, got {kinds}"
        assert all(i["title"] and i["why"] for i in items)

    def test_summary_is_populated_not_the_empty_state(self, client):
        summary = client.get("/api/dashboard").json()["summary"]
        assert summary["assets_tracked"] > 0
        assert summary["skills_tracked"] > 0
        assert summary["job_matches"] > 0
        assert "Not enough data" not in summary["headline"]

    def test_works_with_zero_api_keys_configured(self, client, settings):
        """The non-negotiable requirement: no keys, no external services."""
        assert settings.llm_api_key is None
        assert settings.adzuna_app_id is None
        assert settings.demo_mode is True
        body = client.get("/api/dashboard").json()
        assert body["financial_pulse"] and body["daily_tune"]
        # Every explanation came from the offline templated explainer.
        for entry in body["financial_pulse"]:
            assert entry["explanation"]["generated_by"] == "templated"

    def test_dashboard_on_an_unseeded_database_is_a_clean_404(self, empty_client):
        """No data must produce an honest error, not a crash or fake content."""
        assert empty_client.get("/api/dashboard").status_code == 404

    def test_seed_endpoint_populates_an_empty_database(self, empty_client):
        assert empty_client.post("/api/system/seed").json()["skipped"] is False
        assert empty_client.get("/api/dashboard").status_code == 200
