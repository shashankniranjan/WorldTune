"""Central configuration for WorldTune.

Mirrors the WorldPulse pattern (pydantic-settings, everything overridable by
env var / .env) but is a *separate* settings object: WorldTune never imports
from `worldpulse.*`, the two products stay decoupled.

Design rule: every setting has a working default, and every credential
defaults to None. A provider whose credential is missing disables itself via
`is_available()` rather than raising, so the app always boots.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Operating mode -----------------------------------------------------
    # DEMO_MODE=true (the default) is the primary, fully-reliable path: every
    # provider resolves to its deterministic seeded Demo* adapter and no
    # outbound HTTP happens at all. Set false to attempt the real adapters.
    demo_mode: bool = True

    # Seed demo data at startup if the database is empty.
    auto_seed: bool = True

    # --- Storage ------------------------------------------------------------
    # SQLite default => tests and the demo need zero external services.
    database_url: str = "sqlite:///./worldtune.db"

    # --- Optional free-registration provider credentials --------------------
    adzuna_app_id: str | None = None
    adzuna_app_key: str | None = None
    github_token: str | None = None

    # --- Optional LLM explanation layer -------------------------------------
    # Absent key => TemplatedExplainer. See app/llm/explainer.py.
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"

    # --- HTTP client behaviour (outbound, provider adapters) ----------------
    http_timeout_seconds: float = 10.0
    http_max_retries: int = 3
    http_backoff_base_seconds: float = 0.5
    http_user_agent: str = "WorldTune/0.1 (prototype; contact: ops@worldtune.local)"

    # --- API safety (inbound) ----------------------------------------------
    request_timeout_seconds: float = 20.0
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60

    # --- Persona ------------------------------------------------------------
    default_persona_id: str = "persona-demo-001"

    # --- Model bookkeeping --------------------------------------------------
    # Stamped onto every stored prediction so that a model change is
    # distinguishable from a data change when evaluating accuracy.
    model_version: str = "worldtune-v0.1.0"


settings = Settings()
