"""Central configuration for WorldPulse.

All tunable thresholds and connection settings live here so that every
module (ingestion, prediction, evaluation, API, dashboard, jobs) reads the
same values. Uses pydantic-settings so values can be overridden via
environment variables or a `.env` file without code changes.

Data-source policy (see docs/data-sources.md):
  * `worldpulse_mode` defaults to "free": only zero-cost providers are
    allowed to run. Providers that need a paid subscription (World
    Monitor) are hard-skipped in this mode.
  * `event_providers` defaults to the four no-key-required open feeds.
    Providers whose (free) registration key is absent disable themselves
    via `is_available()` rather than crashing -- see
    `worldpulse.ingestion.providers.registry`.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

# Providers that require a paid subscription. In WORLDPULSE_MODE=free these
# are refused even if explicitly listed in EVENT_PROVIDERS.
PAID_PROVIDERS: frozenset[str] = frozenset({"worldmonitor"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Operating mode ---
    # "free"  -> only zero-cost providers may run (default)
    # "paid"  -> paid providers (World Monitor) may also be selected
    worldpulse_mode: str = "free"

    # --- Event providers ---
    # Comma-separated list. Default = the four feeds that need NO key at all.
    # `firms`, `acled` need a free registration key; `worldmonitor` is paid;
    # `synthetic` is the offline deterministic demo source.
    event_providers: str = "gdelt,usgs,eonet,gdacs"

    # Classifier backend: "rules" (default, no key) or "llm".
    ai_classifier: str = "rules"

    # --- External data sources ---
    # Optional PAID.
    worldmonitor_api_key: str | None = None
    # Optional FREE registration keys.
    nasa_firms_api_key: str | None = None
    fred_api_key: str | None = None
    eia_api_key: str | None = None
    acled_email: str | None = None
    acled_password: str | None = None
    # Optional LLM keys (never required; AI_CLASSIFIER=rules needs none).
    openai_api_key: str | None = None
    groq_api_key: str | None = None
    openrouter_api_key: str | None = None

    # --- Market data ---
    # "synthetic" (default, deterministic/offline), "binance", "stooq", "yfinance".
    market_data_provider: str = "synthetic"

    # --- Database ---
    database_url: str = "sqlite:///./worldpulse.db"

    # --- HTTP client behaviour (shared by every provider) ---
    http_timeout_seconds: float = 20.0
    http_max_retries: int = 3
    http_backoff_base_seconds: float = 0.5
    http_user_agent: str = "WorldPulse/0.1 (+https://github.com/worldpulse) research prototype"

    # --- Provider fetch limits ---
    gdelt_max_records: int = 75
    usgs_min_magnitude: float = 4.5
    firms_cluster_radius_km: float = 50.0
    firms_cluster_window_hours: float = 24.0
    firms_min_cluster_detections: int = 5

    # --- Prediction thresholds (see docs/LLD.md for rationale) ---
    impact_threshold: float = 0.60

    # Confidence tier thresholds: (min_sample_size, min_probability)
    high_confidence_min_n: int = 30
    high_confidence_min_p: float = 0.70
    medium_confidence_min_n: int = 15
    medium_confidence_min_p: float = 0.62
    low_confidence_min_n: int = 10
    low_confidence_min_p: float = 0.57

    # Below this sample size, never predict.
    min_sample_size: int = 10
    # Probability band considered "no signal" regardless of sample size.
    no_signal_low: float = 0.45
    no_signal_high: float = 0.55

    # Dedup clustering
    dedup_window_hours: float = 6.0
    dedup_similarity_threshold: float = 0.55
    # Cross-source (different-provider) merge rule -- see
    # events/deduplication.py. Point-located disasters use the tighter
    # geo window; everything else falls back to `dedup_window_hours`.
    cross_source_window_hours: float = 6.0
    cross_source_geo_window_hours: float = 2.0
    cross_source_geo_radius_km: float = 150.0

    # Similarity retrieval
    similarity_top_k: int = 50

    # --- Impact channel mapping table ---
    impact_channels_path: str = "config/impact_channels.yaml"

    # --- Scheduler intervals (seconds) ---
    news_ingest_interval_seconds: int = 300
    market_ingest_interval_seconds: int = 300
    prediction_interval_seconds: int = 600
    resolution_interval_seconds: int = 900

    # --- Country focus ---
    # ISO-3166 alpha-2 code (e.g. "IN"). When set, event providers that
    # support server-side geographic filtering (GDELT query, USGS FDSN
    # bounding box) narrow their fetch to that country/region, and providers
    # that don't (EONET, GDACS) filter their results client-side by
    # coordinates/country after fetching. Leave unset (None) for the
    # default global feed. See ingestion/providers/country_focus.py.
    country_focus: str | None = None

    # --- Misc ---
    random_seed: int = 42

    # --- Derived helpers ---

    @property
    def is_free_mode(self) -> bool:
        return self.worldpulse_mode.strip().lower() == "free"

    @property
    def data_mode(self) -> str:
        """Human-facing mode label surfaced on /health."""
        return "FREE" if self.is_free_mode else "PAID"

    def provider_names(self) -> list[str]:
        """EVENT_PROVIDERS parsed into a de-duplicated, lowercased list."""
        out: list[str] = []
        for raw in (self.event_providers or "").split(","):
            name = raw.strip().lower()
            if name and name not in out:
                out.append(name)
        return out


settings = Settings()
