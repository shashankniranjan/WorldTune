"""Persona request/response schemas (spec section 3) and the seeded demo
persona (spec section 2).

The persona is the single input that makes WorldTune a personalization
product rather than a news reader: every relevance score, every ranking and
every recommendation is computed against these fields.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Location(BaseModel):
    city: str = ""
    country: str = ""
    timezone: str = "UTC"


class CareerProfile(BaseModel):
    current_role: str = ""
    years_experience: int = 0
    target_roles: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    industry: str = ""


class FinancialProfile(BaseModel):
    asset_classes: list[str] = Field(default_factory=list)
    watchlist: list[str] = Field(default_factory=list)
    # User-declared exposures used for relevance and impact explanations.
    # These are labels/symbols only; quantities and account credentials do not
    # belong in the persona or news pipeline.
    holdings: list[str] = Field(default_factory=list)
    sectors: list[str] = Field(default_factory=list)
    risk_appetite: Literal["low", "medium", "high"] = "medium"


class Preferences(BaseModel):
    learning_topics: list[str] = Field(default_factory=list)
    content_depth: Literal["skim", "balanced", "deep"] = "balanced"
    daily_time_budget_minutes: int = 20


class PersonaBase(BaseModel):
    name: str = ""
    location: Location = Field(default_factory=Location)
    career: CareerProfile = Field(default_factory=CareerProfile)
    financial: FinancialProfile = Field(default_factory=FinancialProfile)
    preferences: Preferences = Field(default_factory=Preferences)


class PersonaUpdate(PersonaBase):
    """PUT /api/persona body. Whole-document replace of the editable fields."""


class Persona(PersonaBase):
    """GET /api/persona response."""

    id: str
    user_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# --- The seeded demo persona, verbatim from spec section 2 -------------------
DEMO_USER_ID = "user-demo-001"
DEMO_USER_EMAIL = "demo@worldtune.local"

DEMO_PERSONA = PersonaBase(
    name="Senior Data Engineer (Bengaluru)",
    location=Location(city="Bengaluru", country="India", timezone="Asia/Kolkata"),
    career=CareerProfile(
        current_role="Senior Data Engineer",
        years_experience=10,
        target_roles=[
            "Staff Data Engineer",
            "Data Platform Engineer",
            "AI Data Engineer",
            "ML Platform Engineer",
        ],
        skills=["Python", "Spark", "Kafka", "SQL", "GCP", "BigQuery", "Airflow", "dbt"],
        industry="technology",
    ),
    financial=FinancialProfile(
        asset_classes=["crypto", "commodities", "equities"],
        watchlist=["BTC", "ETH"],
        holdings=["gold", "silver", "HINDALCO"],
        sectors=["AI", "technology", "crypto"],
        risk_appetite="medium",
    ),
    preferences=Preferences(
        learning_topics=[
            "AI engineering",
            "LLM systems",
            "data infrastructure",
            "distributed systems",
            "agent infrastructure",
        ],
        content_depth="balanced",
        daily_time_budget_minutes=20,
    ),
)
