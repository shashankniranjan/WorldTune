"""Deduplication, the entity graph, and the deterministic embedding."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.db import session_scope
from app.entities.graph import get_entity_graph
from app.ranking.embedding import cosine_similarity, embed_text, tokenize
from app.repositories.dedup import content_hash, job_hash, news_hash, normalize_text
from app.schemas.canonical import CanonicalJob, CanonicalNewsEvent

NOW = datetime(2025, 9, 13, 12, 0, tzinfo=timezone.utc)


class TestNormalization:
    def test_strips_punctuation_and_case(self):
        assert normalize_text("Nvidia's Q3: BEATS!") == "nvidia s q3 beats"

    def test_collapses_whitespace(self):
        assert normalize_text("a   b\n\tc") == "a b c"


class TestContentHash:
    def test_same_headline_different_punctuation_collides(self):
        assert news_hash("Nvidia beats estimates!") == news_hash("Nvidia beats estimates")

    def test_case_insensitive(self):
        assert news_hash("BITCOIN RALLIES") == news_hash("bitcoin rallies")

    def test_different_headlines_do_not_collide(self):
        assert news_hash("Bitcoin rallies") != news_hash("Bitcoin crashes")

    def test_stopwords_are_ignored(self):
        assert news_hash("The Bitcoin rally") == news_hash("Bitcoin rally")

    def test_empty_input_yields_empty_hash(self):
        assert content_hash("") == ""

    def test_job_hash_includes_location(self):
        """Parallel openings in different cities are different jobs."""
        a = job_hash("Data Engineer", "Acme", "Bengaluru")
        b = job_hash("Data Engineer", "Acme", "London")
        assert a != b

    def test_same_job_on_two_boards_collides(self):
        assert job_hash("Senior Data Engineer", "Acme", "Bengaluru") == \
            job_hash("senior data engineer", "ACME", "bengaluru")


class TestDedupOnIngest:
    def test_duplicate_headline_from_two_sources_stored_once(self, session):
        from app.repositories.ingest import ingest_news

        title = "Nvidia beats revenue estimates on AI demand"
        events = [
            CanonicalNewsEvent(title=title, published_at=NOW, source="gdelt",
                               domain="reuters.com"),
            CanonicalNewsEvent(title=title + "!", published_at=NOW,
                               source="google-news-rss", domain="cnbc.com"),
        ]
        assert ingest_news(session, events) == 1

    def test_duplicate_job_across_boards_stored_once(self, session):
        from app.repositories.ingest import ingest_jobs

        jobs = [
            CanonicalJob(external_id="1", title="Senior Data Engineer", company="Acme",
                         location="Bengaluru, India", posted_at=NOW, source="remoteok",
                         description="Spark and Kafka"),
            CanonicalJob(external_id="2", title="senior data engineer", company="ACME",
                         location="bengaluru, india", posted_at=NOW, source="adzuna",
                         description="Spark and Kafka"),
        ]
        assert ingest_jobs(session, jobs) == 1

    def test_reingestion_is_idempotent(self, session):
        from app.repositories.ingest import ingest_news

        events = [CanonicalNewsEvent(title="Bitcoin rallies past $64,000",
                                     published_at=NOW, source="demo:news")]
        assert ingest_news(session, events) == 1
        assert ingest_news(session, events) == 0

    def test_seeded_database_has_no_duplicate_hashes(self, seeded):
        from sqlalchemy import func, select

        from app.models import JobORM, NewsEventORM

        with session_scope() as s:
            for model in (NewsEventORM, JobORM):
                total = s.scalar(select(func.count()).select_from(model))
                distinct = s.scalar(select(func.count(func.distinct(model.dedup_hash))))
                assert total == distinct, f"{model.__name__} has duplicate dedup_hash rows"


class TestEntityGraph:
    def test_config_loads(self):
        graph = get_entity_graph()
        assert "nvidia" in graph.nodes
        assert graph.nodes["nvidia"].tickers == ("NVDA",)

    def test_resolves_aliases(self):
        graph = get_entity_graph()
        assert "nvidia" in graph.resolve_text("NVDA reports earnings")
        assert "bitcoin" in graph.resolve_text("btc is up")

    def test_longest_alias_wins(self):
        """'apache iceberg' must beat a bare 'iceberg' match."""
        graph = get_entity_graph()
        assert "lakehouse" in graph.resolve_text("Apache Iceberg adoption grows")

    def test_word_boundaries_prevent_substring_matches(self):
        graph = get_entity_graph()
        assert "ai" not in graph.resolve_text("the plaid chair")

    def test_expansion_decays_with_distance(self):
        graph = get_entity_graph()
        weights = graph.expand(["nvidia"])
        assert weights["nvidia"] == pytest.approx(1.0)
        assert weights["ai"] == pytest.approx(graph.decay)
        assert weights["ai"] > weights.get("llm", 0.0)

    def test_expansion_respects_max_hops(self):
        graph = get_entity_graph()
        assert len(graph.expand(["nvidia"], max_hops=0)) == 1

    def test_spec_example_path_nvidia_to_ai_infrastructure(self):
        """Spec 28: NVIDIA -> AI -> semiconductors -> tech stocks -> CUDA -> AI infra."""
        weights = get_entity_graph().expand(["nvidia"])
        for node in ("ai", "semiconductors", "technology-stocks", "cuda", "ai-infrastructure"):
            assert node in weights, f"{node} unreachable from nvidia"

    def test_spec_example_path_databricks(self):
        """Spec 28: Databricks -> Data Engineering -> Spark -> Lakehouse -> AI Data Platform."""
        weights = get_entity_graph().expand(["databricks"])
        for node in ("data-engineering", "spark", "lakehouse", "ai-data-platform"):
            assert node in weights, f"{node} unreachable from databricks"

    def test_tickers_and_sectors_lookup(self):
        graph = get_entity_graph()
        keys = graph.resolve_text("NVIDIA announces new AI chips")
        assert "NVDA" in graph.tickers_for(keys)
        assert graph.sectors_for(keys)


class TestEmbedding:
    def test_deterministic(self):
        assert embed_text("spark kafka airflow") == embed_text("spark kafka airflow")

    def test_l2_normalized(self):
        vec = embed_text("data engineering with spark")
        assert sum(v * v for v in vec) == pytest.approx(1.0)

    def test_empty_text_is_zero_vector(self):
        assert all(v == 0.0 for v in embed_text(""))

    def test_identical_text_has_similarity_one(self):
        vec = embed_text("staff data engineer")
        assert cosine_similarity(vec, vec) == pytest.approx(1.0)

    def test_overlapping_text_beats_unrelated_text(self):
        persona = embed_text("data engineer spark kafka airflow")
        related = embed_text("senior data engineer working on spark pipelines")
        unrelated = embed_text("pastry chef bakery sourdough")
        assert cosine_similarity(persona, related) > cosine_similarity(persona, unrelated)

    def test_similarity_is_bounded(self):
        a, b = embed_text("alpha beta"), embed_text("gamma delta")
        assert 0.0 <= cosine_similarity(a, b) <= 1.0

    def test_mismatched_dimensions_return_zero(self):
        assert cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0]) == 0.0

    def test_stopwords_are_dropped(self):
        assert "the" not in tokenize("the spark of the engine")

    def test_sublinear_term_frequency(self):
        """Nine mentions of Spark is not nine times more about Spark."""
        once = embed_text("spark kafka")
        many = embed_text("spark spark spark spark spark kafka")
        assert cosine_similarity(once, many) > 0.5
