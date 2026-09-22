"""Central configuration for WorldTune.

Mirrors the WorldPulse pattern (pydantic-settings, everything overridable by
env var / .env) but is a *separate* settings object: WorldTune never imports
from `worldpulse.*`, the two products stay decoupled.

Design rule: every setting has a working default, and every credential
defaults to None. A provider whose credential is missing disables itself via
`is_available()` rather than raising, so the app always boots.
"""
from __future__ import annotations

from pydantic import AliasChoices, Field
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
    llm_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LLM_API_KEY", "OPENROUTER_API_KEY"),
    )
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "google/gemini-2.5-flash"
    world_shift_prompt_version: str = "world-shift-v4-full-briefings"
    world_shift_schema_version: str = "2.1"
    world_shift_refresh_max_shifts: int = 20
    world_shift_ai_enabled: bool = True
    world_shift_auto_refresh_enabled: bool = True
    # Background refresh cadence; reads continue serving the last ACTIVE snapshot.
    world_shift_refresh_interval_seconds: int = 86400
    world_shift_refresh_startup_delay_seconds: int = 5
    world_shift_web_research_enabled: bool = True
    # Raised from 3: GDELT GKG metadata alone rarely carries enough prose for
    # the grounding filters to pass anything. More researched sources per
    # shift gives the semantic-extraction stage real specifics to ground on.
    world_shift_web_results_per_shift: int = 8
    world_shift_web_research_ttl_seconds: int = 21600

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
