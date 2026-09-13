"""Skill taxonomy, extraction and demand metrics."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.skills.extraction import extract_skill_ids, extract_skills, normalize_persona_skills
from app.skills.taxonomy import SKILLS, SKILLS_BY_ID, skill_id_for


class TestTaxonomy:
    def test_ids_are_unique(self):
        assert len({s.id for s in SKILLS}) == len(SKILLS)

    def test_spec_categories_are_populated(self):
        categories = {s.category for s in SKILLS}
        assert {"data-engineering", "ai-ml", "cloud"} <= categories

    def test_spec_named_skills_all_present(self):
        """The section-9 vocabulary must exist -- it is the unit of analysis."""
        required = ["spark", "kafka", "airflow", "dbt", "snowflake", "databricks",
                    "bigquery", "redshift", "flink", "iceberg", "delta-lake",
                    "pytorch", "tensorflow", "llm", "rag", "langchain", "langgraph",
                    "vector-database", "embeddings", "agents", "mlops",
                    "aws", "gcp", "azure", "kubernetes", "docker"]
        missing = [r for r in required if r not in SKILLS_BY_ID]
        assert missing == []

    def test_lookup_by_name_and_alias(self):
        assert skill_id_for("Spark") == "spark"
        assert skill_id_for("apache spark") == "spark"
        assert skill_id_for("PySpark") == "spark"
        assert skill_id_for("nonsense") is None


class TestExtraction:
    def test_extracts_multiple_skills(self):
        found = extract_skills("We use Spark, Kafka and Airflow daily.")
        assert set(found) == {"spark", "kafka", "airflow"}

    def test_counts_repeated_mentions(self):
        assert extract_skills("Spark spark SPARK")["spark"] == 3

    def test_word_boundaries_prevent_false_positives(self):
        """'ML' must not fire inside 'HTML'; 'SQL' must not fire inside 'NoSQLish'."""
        assert extract_skills("We write HTML and NoSQLish code") == {}

    def test_longest_phrase_wins_and_is_not_double_counted(self):
        found = extract_skills("We run Delta Lake tables")
        assert found.get("delta-lake") == 1

    def test_aliases_map_to_canonical_id(self):
        assert "vector-database" in extract_skills("we use Pinecone and Weaviate")
        assert extract_skills("we use Pinecone and Weaviate")["vector-database"] == 2

    def test_empty_text(self):
        assert extract_skills("") == {}

    def test_extract_ids_ordered_by_frequency(self):
        ids = extract_skill_ids("kafka kafka kafka spark")
        assert ids[0] == "kafka"

    def test_normalize_persona_skills(self):
        result = normalize_persona_skills(["Python", "Spark", "Google BigQuery", "Underwater Basketweaving"])
        assert "python" in result and "spark" in result and "bigquery" in result
        assert len(result) == 3   # the unknown entry is dropped from the canonical view

    def test_normalize_is_deduplicated(self):
        assert normalize_persona_skills(["Spark", "PySpark", "apache spark"]) == ["spark"]


class TestSkillMetrics:
    def test_share_is_normalized_by_posting_volume(self, seeded):
        """skill_share must be mentions/job_count, not a raw count."""
        from app.db import session_scope
        from app.skills.metrics import latest_metrics

        with session_scope() as s:
            metrics = latest_metrics(s)
        assert metrics
        for metric in metrics.values():
            assert metric.job_count > 0
            assert metric.skill_share == pytest.approx(
                metric.skill_mentions / metric.job_count)
            assert 0.0 <= metric.skill_share <= 1.0

    def test_history_exists_so_changes_are_computable(self, seeded):
        from app.db import session_scope
        from app.skills.metrics import skill_share_series

        with session_scope() as s:
            series = skill_share_series(s, "spark")
        assert len(series) >= 30   # not a single snapshot

    def test_seeded_rising_skills_show_positive_30d_change(self, seeded):
        """The demo drift must survive all the way into the metrics table."""
        from app.db import session_scope
        from app.skills.metrics import latest_metrics

        with session_scope() as s:
            metrics = latest_metrics(s)
        rising = [sid for sid in ("llm", "rag", "agents", "iceberg")
                  if sid in metrics and metrics[sid].change_30d > 0]
        assert rising, "expected at least one seeded rising skill to trend up"

    def test_scopes_are_stored_separately(self, seeded):
        from app.db import session_scope
        from app.skills.metrics import latest_metrics

        with session_scope() as s:
            glob = latest_metrics(s, scope_type="global")
            local = latest_metrics(s, scope_type="location", scope_value="Bengaluru")
        assert glob and local
        # Bengaluru is a strict subset of the board, so its denominator is smaller.
        any_skill = next(iter(local))
        assert local[any_skill].job_count <= glob[any_skill].job_count

    def test_metrics_do_not_leak_future_data(self, seeded):
        """A row's change_7d must be computed from its own prefix only."""
        from app.db import session_scope
        from sqlalchemy import select
        from app.models import SkillMetricORM

        with session_scope() as s:
            rows = s.scalars(
                select(SkillMetricORM)
                .where(SkillMetricORM.skill_id == "spark")
                .where(SkillMetricORM.scope_type == "global")
                .order_by(SkillMetricORM.as_of)
            ).all()
        # The earliest rows cannot have a 30-day change: there is no 30-day prefix.
        assert rows[0].change_30d == 0.0
        assert rows[0].change_7d == 0.0
