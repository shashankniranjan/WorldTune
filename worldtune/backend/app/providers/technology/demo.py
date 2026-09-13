"""Deterministic demo technology signals -- the DEMO_MODE=true path.

24 technologies with a *weekly snapshot history* rather than a single point,
because the interesting quantity for Career Pulse is velocity, not level:
"Apache Iceberg gained 2,100 stars in 7 days" is a career signal; "Apache
Iceberg has 6,000 stars" is trivia.

Each technology carries a growth regime (hot / warm / flat / cooling) that
determines its star and discussion trajectory across the snapshots, and each
declares the skills it implies -- that link is what lets a technology signal
raise the score of a *skill* the persona does not yet have.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import numpy as np

from app.providers.base import TechnologySignalsProvider
from app.schemas.canonical import CanonicalTechEvent


@dataclass(frozen=True)
class DemoTechSpec:
    name: str
    category: str
    headline: str
    base_stars: float
    weekly_growth: float      # fractional star growth per week
    base_points: float
    related_skills: tuple[str, ...]


DEMO_TECHNOLOGIES: tuple[DemoTechSpec, ...] = (
    DemoTechSpec("Apache Iceberg", "data-infrastructure",
                 "Iceberg becomes the default open table format across vendors",
                 6820, 0.061, 340, ("iceberg", "spark", "databricks")),
    DemoTechSpec("LLM observability", "ai-tooling",
                 "LLM observability tooling consolidates around OpenTelemetry",
                 3410, 0.084, 410, ("llm", "mlops")),
    DemoTechSpec("Agent frameworks", "ai-tooling",
                 "Production agent frameworks add durable execution",
                 11240, 0.093, 680, ("agents", "langgraph", "llm")),
    DemoTechSpec("Databricks ecosystem", "data-infrastructure",
                 "Unity Catalog opens to external Iceberg catalogs",
                 4190, 0.037, 260, ("databricks", "spark", "delta-lake")),
    DemoTechSpec("DuckDB", "data-infrastructure",
                 "DuckDB pushes into production analytics workloads",
                 22800, 0.048, 520, ("sql", "python")),
    DemoTechSpec("LangGraph", "ai-tooling",
                 "LangGraph adopted for stateful agent orchestration",
                 7650, 0.071, 300, ("langgraph", "agents", "llm")),
    DemoTechSpec("dbt semantic layer", "data-infrastructure",
                 "Semantic layer standardization gathers pace",
                 2980, 0.022, 150, ("dbt", "sql")),
    DemoTechSpec("Apache Flink", "data-infrastructure",
                 "Flink gains ground as batch pipelines migrate to streaming",
                 23100, 0.014, 130, ("flink", "kafka")),
    DemoTechSpec("Vector databases", "ai-tooling",
                 "Vector search folds into mainstream databases",
                 9420, 0.029, 390, ("vector-database", "embeddings", "rag")),
    DemoTechSpec("RAG pipelines", "ai-tooling",
                 "Retrieval quality, not model size, dominates RAG results",
                 8130, 0.055, 470, ("rag", "embeddings", "llm")),
    DemoTechSpec("Delta Lake", "data-infrastructure",
                 "Delta Lake interoperability improves with UniForm",
                 7380, 0.019, 120, ("delta-lake", "databricks", "spark")),
    DemoTechSpec("Kubernetes operators for data", "platform",
                 "Data workloads standardize on Kubernetes operators",
                 5210, 0.017, 110, ("kubernetes", "docker")),
    DemoTechSpec("MLflow", "ai-tooling",
                 "MLflow extends tracking to LLM evaluation",
                 18300, 0.021, 140, ("mlops", "pytorch")),
    DemoTechSpec("Feature stores", "ai-tooling",
                 "Feature store interest cools as teams simplify",
                 4820, -0.008, 60, ("mlops", "spark")),
    DemoTechSpec("Airflow 3", "data-infrastructure",
                 "Airflow 3 lands with a rewritten scheduler",
                 35600, 0.016, 290, ("airflow", "python")),
    DemoTechSpec("Kafka tiered storage", "data-infrastructure",
                 "Tiered storage cuts Kafka retention costs",
                 2640, 0.026, 95, ("kafka", "streaming")),
    DemoTechSpec("Polars", "data-infrastructure",
                 "Polars adoption grows for single-node transforms",
                 29400, 0.043, 310, ("python", "sql")),
    DemoTechSpec("Ray", "ai-tooling",
                 "Ray becomes the scaling layer for LLM workloads",
                 33100, 0.033, 210, ("python", "mlops", "pytorch")),
    DemoTechSpec("Snowflake Cortex", "data-infrastructure",
                 "Warehouses ship native LLM functions",
                 1890, 0.031, 130, ("snowflake", "llm", "sql")),
    DemoTechSpec("BigQuery vector search", "data-infrastructure",
                 "BigQuery adds native vector indexes",
                 1420, 0.038, 105, ("bigquery", "vector-database", "gcp")),
    DemoTechSpec("Hadoop / legacy ETL", "data-infrastructure",
                 "Legacy Hadoop workloads continue migrating off-platform",
                 12800, -0.021, 25, ("spark",)),
    DemoTechSpec("Model Context Protocol", "ai-tooling",
                 "MCP standardizes tool access for agents",
                 5940, 0.112, 730, ("agents", "llm")),
    DemoTechSpec("Prompt evaluation harnesses", "ai-tooling",
                 "Eval harnesses become table stakes for LLM teams",
                 3270, 0.064, 280, ("llm", "mlops")),
    DemoTechSpec("Data contracts", "data-infrastructure",
                 "Data contracts move from blog posts to tooling",
                 2110, 0.024, 90, ("dbt", "sql")),
)

DEMO_TECH_BY_NAME = {t.name: t for t in DEMO_TECHNOLOGIES}
SNAPSHOT_WEEKS = 8


class DemoTechnologyProvider(TechnologySignalsProvider):
    name = "demo:technology"
    is_live = False

    def __init__(self, as_of: datetime | None = None, seed: int = 77):
        self._as_of = as_of or datetime.now(timezone.utc)
        self._seed = seed

    def is_available(self) -> bool:
        return True

    def related_skills(self, tech_name: str) -> list[str]:
        spec = DEMO_TECH_BY_NAME.get(tech_name)
        return list(spec.related_skills) if spec else []

    def fetch_tech_events(self, *, topics: list[str] | None = None,
                          limit: int = 50) -> list[CanonicalTechEvent]:
        rng = np.random.default_rng(self._seed)
        wanted = {t.lower() for t in (topics or [])}
        events: list[CanonicalTechEvent] = []
        for spec in DEMO_TECHNOLOGIES:
            if wanted and spec.name.lower() not in wanted and spec.category.lower() not in wanted:
                continue
            prev_stars = None
            # Oldest snapshot first so `stars_7d_delta` is a true difference
            # against the immediately preceding week.
            for week in range(SNAPSHOT_WEEKS - 1, -1, -1):
                noise = 1.0 + float(rng.normal(0, 0.01))
                stars = spec.base_stars * ((1.0 + spec.weekly_growth) ** (-week)) * noise
                delta = 0.0 if prev_stars is None else stars - prev_stars
                prev_stars = stars
                events.append(
                    CanonicalTechEvent(
                        name=spec.name,
                        title=spec.headline,
                        category=spec.category,
                        url=f"https://tech.worldtune.local/demo/{spec.name.lower().replace(' ', '-')}",
                        source="demo:technology",
                        observed_at=self._as_of - timedelta(weeks=week),
                        stars=round(stars, 1),
                        stars_7d_delta=round(delta, 1),
                        points=round(spec.base_points * (1.0 + spec.weekly_growth) ** (-week), 1),
                        mentions=round(max(0.0, spec.base_points / 6.0 * noise), 1),
                    )
                )
        return events[:limit] if limit and limit < len(events) else events
