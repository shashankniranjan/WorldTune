"""Skill taxonomy (spec section 9).

A dictionary, on purpose. The taxonomy is the unit of analysis for Career
Pulse -- every skill metric, every "learn this" recommendation and every gap
calculation keys off these canonical slugs -- so it must be stable,
inspectable and diffable. Aliases exist because job descriptions spell the
same skill six ways ("PySpark", "Apache Spark", "Spark 3.x").
"""
from __future__ import annotations

from dataclasses import dataclass

CATEGORY_DATA_ENGINEERING = "data-engineering"
CATEGORY_AI_ML = "ai-ml"
CATEGORY_CLOUD = "cloud"


@dataclass(frozen=True)
class Skill:
    id: str
    name: str
    category: str
    aliases: tuple[str, ...] = ()


def _s(id_: str, name: str, category: str, *aliases: str) -> Skill:
    return Skill(id=id_, name=name, category=category, aliases=tuple(aliases))


SKILLS: tuple[Skill, ...] = (
    # --- Data Engineering ---------------------------------------------------
    _s("spark", "Spark", CATEGORY_DATA_ENGINEERING, "apache spark", "pyspark", "spark sql"),
    _s("kafka", "Kafka", CATEGORY_DATA_ENGINEERING, "apache kafka", "kafka streams"),
    _s("airflow", "Airflow", CATEGORY_DATA_ENGINEERING, "apache airflow", "mwaa", "composer"),
    _s("dbt", "dbt", CATEGORY_DATA_ENGINEERING, "data build tool", "dbt core", "dbt cloud"),
    _s("snowflake", "Snowflake", CATEGORY_DATA_ENGINEERING),
    _s("databricks", "Databricks", CATEGORY_DATA_ENGINEERING, "unity catalog"),
    _s("bigquery", "BigQuery", CATEGORY_DATA_ENGINEERING, "big query"),
    _s("redshift", "Redshift", CATEGORY_DATA_ENGINEERING, "amazon redshift"),
    _s("flink", "Flink", CATEGORY_DATA_ENGINEERING, "apache flink"),
    _s("iceberg", "Iceberg", CATEGORY_DATA_ENGINEERING, "apache iceberg", "iceberg tables"),
    _s("delta-lake", "Delta Lake", CATEGORY_DATA_ENGINEERING, "deltalake", "delta tables"),
    _s("sql", "SQL", CATEGORY_DATA_ENGINEERING, "ansi sql", "t-sql"),
    _s("python", "Python", CATEGORY_DATA_ENGINEERING, "python3"),
    # --- AI / ML ------------------------------------------------------------
    _s("pytorch", "PyTorch", CATEGORY_AI_ML, "torch"),
    _s("tensorflow", "TensorFlow", CATEGORY_AI_ML, "tf2", "keras"),
    _s("llm", "LLM", CATEGORY_AI_ML, "llms", "large language model", "large language models",
       "foundation model", "foundation models"),
    _s("rag", "RAG", CATEGORY_AI_ML, "retrieval augmented generation", "retrieval-augmented generation"),
    _s("langchain", "LangChain", CATEGORY_AI_ML, "lang chain"),
    _s("langgraph", "LangGraph", CATEGORY_AI_ML, "lang graph"),
    _s("vector-database", "Vector database", CATEGORY_AI_ML, "vector db", "vector store",
       "pinecone", "weaviate", "pgvector", "milvus", "qdrant"),
    _s("embeddings", "Embeddings", CATEGORY_AI_ML, "embedding models", "sentence transformers"),
    _s("agents", "Agents", CATEGORY_AI_ML, "agentic", "ai agents", "agent framework",
       "agent frameworks", "multi-agent"),
    _s("mlops", "MLOps", CATEGORY_AI_ML, "ml ops", "model serving", "mlflow", "feature store"),
    # --- Cloud --------------------------------------------------------------
    _s("aws", "AWS", CATEGORY_CLOUD, "amazon web services"),
    _s("gcp", "GCP", CATEGORY_CLOUD, "google cloud", "google cloud platform"),
    _s("azure", "Azure", CATEGORY_CLOUD, "microsoft azure"),
    _s("kubernetes", "Kubernetes", CATEGORY_CLOUD, "k8s", "eks", "gke"),
    _s("docker", "Docker", CATEGORY_CLOUD, "containers", "containerization"),
)

SKILLS_BY_ID: dict[str, Skill] = {s.id: s for s in SKILLS}

# name/alias (lowercased) -> skill id. Built once; used by the extractor.
SKILL_LOOKUP: dict[str, str] = {}
for _skill in SKILLS:
    SKILL_LOOKUP[_skill.name.lower()] = _skill.id
    for _alias in _skill.aliases:
        SKILL_LOOKUP[_alias.lower()] = _skill.id


def skill_id_for(text: str) -> str | None:
    """Canonical skill id for a free-text skill name, or None."""
    return SKILL_LOOKUP.get(text.strip().lower())


def skills_in_category(category: str) -> list[Skill]:
    return [s for s in SKILLS if s.category == category]
