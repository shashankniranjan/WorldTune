from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy import func, select

from app.db import session_scope
from app.models import AIGenerationORM, WorldShiftRefreshRunORM, WorldShiftSnapshotORM
from app.schemas.world_shift import PersonaSynthesis, SemanticExtraction, WorldShiftSynthesis
from app.services import world_shift_refresh as refresh_module
from app.services.world_shift_ai import (
    IntelligenceValidationError, WorldShiftGenerationService, WorldShiftWebResearchService,
    validate_grounding,
)
from app.services.world_shift_refresh import RefreshService, _persist_semantics, promote_snapshot


EVIDENCE = [{
    "evidenceId": "ev_alpha", "url": "https://example.com/report", "source": "example.com",
    "sourceDomain": "example.com", "originalHeadline": "Alpha regulates Beta", "publishedAt": "2026-09-19T00:00:00Z",
    "imageUrl": None, "sourceSnippet": "Alpha regulates Beta", "aiSummary": None,
    "tags": ["observed"], "eventIds": [], "claimIds": [], "entityIds": [], "evidenceClass": "observed",
}]


def semantic_payload():
    return {
        "events": [{"eventId": "event_alpha", "title": "Alpha update", "summary": "Alpha regulates Beta",
                    "evidenceIds": ["ev_alpha"], "entityIds": ["entity_alpha", "entity_beta"], "evidenceClass": "observed"}],
        "claims": [{"claimId": "claim_alpha", "text": "Alpha regulates Beta", "evidenceIds": ["ev_alpha"],
                    "entityIds": ["entity_alpha", "entity_beta"], "evidenceClass": "observed"}],
        "entities": [{"entityId": "entity_alpha", "name": "Alpha", "normalizedName": "alpha", "entityType": "organization", "evidenceIds": ["ev_alpha"]},
                     {"entityId": "entity_beta", "name": "Beta", "normalizedName": "beta", "entityType": "organization", "evidenceIds": ["ev_alpha"]}],
        "relationships": [{"relationshipId": "relationship_alpha", "sourceEntityId": "entity_alpha",
                           "targetEntityId": "entity_beta", "relationshipType": "REGULATES", "label": "Alpha regulates Beta",
                           "evidenceClass": "observed", "evidenceIds": ["ev_alpha"], "claimIds": ["claim_alpha"]}],
    }


def test_stage_a_schema_and_grounding_accept_valid_output():
    value = SemanticExtraction.model_validate(semantic_payload())
    validate_grounding(value, EVIDENCE, grounding_input={"evidence": EVIDENCE})


def test_stage_b_and_persona_schemas_validate_grounded_json():
    semantic = SemanticExtraction.model_validate(semantic_payload())
    point = {"text": "Alpha regulates Beta", "evidenceClass": "observed",
             "evidenceIds": ["ev_alpha"], "claimIds": ["claim_alpha"]}
    common = WorldShiftSynthesis.model_validate({"summary": "Alpha regulates Beta", "whatsHappening": [point],
        "whyItMatters": [point], "keyDevelopments": [point], "keyThemes": ["Alpha"], "watchNext": [],
        "quickTake": "Alpha regulates Beta", "relationshipStory": {"why": "Alpha regulates Beta"}})
    validate_grounding(common, EVIDENCE, semantic=semantic, grounding_input={"evidence": EVIDENCE})
    impact = {"id": "impact_alpha", "title": "Alpha", "summary": "Alpha regulates Beta",
              "evidenceClass": "inferred", "evidenceIds": ["ev_alpha"], "claimIds": ["claim_alpha"]}
    persona = PersonaSynthesis.model_validate({"summary": "Alpha regulates Beta", "directImpacts": [impact],
        "risks": [], "opportunities": [], "watchItems": [], "domainGroups": [{"id": "group_alpha",
        "title": "Organizations", "items": [{"id": "domain_alpha", "name": "Alpha", "type": "organization",
        "summary": "Alpha regulates Beta", "evidenceIds": ["ev_alpha"]}]}]})
    validate_grounding(persona, EVIDENCE, semantic=semantic, grounding_input={"evidence": EVIDENCE, "semantic": semantic.model_dump(by_alias=True)})


@pytest.mark.parametrize("mutation, message", [
    (lambda p: p["claims"][0].update(evidenceIds=["ev_invented"]), "invalid evidenceIds"),
    (lambda p: p["relationships"][0].update(claimIds=["claim_invented"]), "invalid claimIds"),
    (lambda p: p["relationships"][0].update(sourceEntityId="entity_invented"), "invalid relationship source"),
])
def test_lineage_validation_rejects_invalid_references(mutation, message):
    payload = semantic_payload(); mutation(payload)
    value = SemanticExtraction.model_validate(payload)
    with pytest.raises(IntelligenceValidationError, match=message):
        validate_grounding(value, EVIDENCE, grounding_input={"evidence": EVIDENCE})


def test_schema_rejects_forbidden_evidence_class():
    payload = semantic_payload(); payload["claims"][0]["evidenceClass"] = "causal"
    with pytest.raises(ValidationError):
        SemanticExtraction.model_validate(payload)


def test_grounding_rejects_ungrounded_entity_and_number():
    payload = semantic_payload(); payload["entities"][0]["name"] = payload["entities"][0]["normalizedName"] = "Gamma"
    with pytest.raises(IntelligenceValidationError, match="ungrounded entity"):
        validate_grounding(SemanticExtraction.model_validate(payload), EVIDENCE, grounding_input={"evidence": EVIDENCE})
    payload = semantic_payload(); payload["claims"][0]["text"] = "Alpha recorded 9876 reports"
    with pytest.raises(IntelligenceValidationError, match="ungrounded number"):
        validate_grounding(SemanticExtraction.model_validate(payload), EVIDENCE, grounding_input={"evidence": EVIDENCE})


def test_grounding_rejects_invented_url():
    class URLResult(BaseModel):
        model_config = ConfigDict(extra="forbid")
        url: str
    with pytest.raises(IntelligenceValidationError, match="invented URL"):
        validate_grounding(URLResult(url="https://invented.example/x"), EVIDENCE)


def test_ai_generation_cache_is_reused(session):
    class FakeClient:
        calls = 0
        def generate(self, **kwargs):
            self.calls += 1
            return kwargs["schema"].model_validate(semantic_payload())
    fake = FakeClient(); service = WorldShiftGenerationService(fake)
    first = service.extract(session, shift_id="alpha", evidence=EVIDENCE, metrics={}, run_id="run_a")
    second = service.extract(session, shift_id="alpha", evidence=EVIDENCE, metrics={}, run_id="run_b")
    assert first == second
    assert fake.calls == 1 and service.reused == 1
    assert session.scalar(select(func.count()).select_from(AIGenerationORM)) == 1


def test_ai_generation_retries_malformed_response_up_to_three_times(session):
    class FlakyClient:
        calls = 0

        def generate(self, **kwargs):
            self.calls += 1
            if self.calls < 3:
                raise ValueError("truncated JSON")
            return kwargs["schema"].model_validate(semantic_payload())

    fake = FlakyClient()
    result = WorldShiftGenerationService(fake).extract(
        session, shift_id="retry", evidence=EVIDENCE, metrics={}, run_id="run_retry"
    )
    assert result.events and fake.calls == 3


def test_web_research_is_bounded_cited_and_cached(session, monkeypatch):
    calls: list[dict] = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"annotations": [
                {"url_citation": {"url": "https://official.example/report", "title": "Official report",
                                  "content": "A concrete observed development."}},
                {"url_citation": {"url": "https://specialist.example/analysis", "title": "Specialist analysis"}},
                {"url_citation": {"url": "https://ignored.example/extra", "title": "Extra result"}},
            ]}}]}

    class FakeHTTPClient:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def post(self, url, *, json, headers):
            calls.append(json)
            return FakeResponse()

    from app.services import world_shift_ai as ai_module
    monkeypatch.setattr(ai_module.settings, "llm_api_key", "test-key")
    monkeypatch.setattr(ai_module.settings, "world_shift_web_research_enabled", True)
    monkeypatch.setattr(ai_module.httpx, "Client", FakeHTTPClient)
    service = WorldShiftWebResearchService()
    first = service.research(session, shift_id="alpha", topic="Alpha", category="technology",
                             evidence=EVIDENCE, run_id="run_web_1", max_results=2)
    second = service.research(session, shift_id="alpha", topic="Alpha", category="technology",
                              evidence=EVIDENCE, run_id="run_web_2", max_results=2)

    assert len(first) == 2 and second == first
    assert len(calls) == 1
    assert calls[0]["tools"][0]["type"] == "openrouter:web_search"
    assert calls[0]["tools"][0]["parameters"]["max_total_results"] == 2
    assert all(item["evidenceClass"] == "observed" and item["url"].startswith("https://") for item in first)


def _snapshot(snapshot_id: str, lifecycle: str) -> WorldShiftSnapshotORM:
    now = datetime.now(timezone.utc)
    return WorldShiftSnapshotORM(snapshot_id=snapshot_id, shift_id="alpha", persona="tech",
        lifecycle=lifecycle, rank=1, payload={"marker": snapshot_id}, generation_run_id="run",
        valid_until=now + timedelta(days=1))


def test_atomic_snapshot_promotion(session):
    session.add_all([_snapshot("old", "ACTIVE"), _snapshot("new", "BUILDING")]); session.commit()
    promote_snapshot("new")
    assert session.scalar(select(WorldShiftSnapshotORM.lifecycle).where(WorldShiftSnapshotORM.snapshot_id == "old")) == "HISTORICAL"
    assert session.scalar(select(WorldShiftSnapshotORM.lifecycle).where(WorldShiftSnapshotORM.snapshot_id == "new")) == "ACTIVE"


def test_duplicate_refresh_returns_existing_run(session, monkeypatch):
    session.add(_snapshot("old", "ACTIVE")); session.commit()
    monkeypatch.setattr(refresh_module._executor, "submit", lambda *args, **kwargs: None)
    service = RefreshService()
    first = service.request_refresh(); second = service.request_refresh()
    assert first.run_id == second.run_id
    assert first.status == second.status == "queued"


def test_failed_refresh_preserves_active_snapshot(session, monkeypatch):
    session.add(_snapshot("old", "ACTIVE"))
    session.add(WorldShiftRefreshRunORM(run_id="run_fail", status="queued", stage="fetching_gdelt",
        completed=0, total=10, current_snapshot_id="old")); session.commit()
    monkeypatch.setattr(refresh_module, "_rows", lambda: (_ for _ in ()).throw(RuntimeError("source unavailable")))
    RefreshService()._run("run_fail")
    assert session.scalar(select(WorldShiftSnapshotORM.lifecycle).where(WorldShiftSnapshotORM.snapshot_id == "old")) == "ACTIVE"
    session.expire_all()
    run = session.get(WorldShiftRefreshRunORM, "run_fail")
    assert run.status == "failed" and "source unavailable" in run.error


def test_refresh_api_creation_duplicate_and_status(client, monkeypatch):
    monkeypatch.setattr(refresh_module._executor, "submit", lambda *args, **kwargs: None)
    first = client.post("/world-shifts/refresh")
    second = client.post("/world-shifts/refresh")
    assert first.status_code == second.status_code == 200
    assert first.json()["runId"] == second.json()["runId"]
    status = client.get(f"/world-shifts/refresh/{first.json()['runId']}")
    assert status.status_code == 200 and status.json()["status"] == "queued"


def test_headline_preserved_and_image_nullable():
    row = {"date": "2026-09-19", "category": "technology", "representative_evidence":
           '[{"title":"Original publisher headline","url":"https://example.com/a","domain":"example.com"}]'}
    evidence = refresh_module._artifact_evidence(row, enrich=False)
    assert evidence[0]["originalHeadline"] == "Original publisher headline"
    assert evidence[0]["imageUrl"] is None


def test_evidence_quality_metadata_and_independent_publishers(monkeypatch):
    monkeypatch.setattr(refresh_module, "_publisher_metadata", lambda url: ("Same event", None, "Useful snippet"))
    row = {"date": "2026-09-19", "category": "technology", "representative_evidence":
           '[{"title":"","url":"https://one.example/a","domain":"one.example"},'
           '{"title":"","url":"https://two.test/b","domain":"two.test"}]'}
    evidence = refresh_module._artifact_evidence(row)
    assert all(item["retrievalStatus"] == "complete" for item in evidence)
    assert all(item["independentPublisherCount"] == 2 for item in evidence)
    assert all(item["corroborationStatus"] == "syndicated" for item in evidence)


def test_publisher_enrichment_failure_keeps_bounded_evidence(monkeypatch):
    monkeypatch.setattr(refresh_module, "_publisher_metadata", lambda url: (None, None, None))
    row = {"date": "2026-09-19", "category": "technology", "representative_evidence":
           '[{"title":"Source report from example.com","url":"https://example.com/a","domain":"example.com"}]'}
    evidence = refresh_module._artifact_evidence(row)
    assert evidence[0]["originalHeadline"] is None and evidence[0]["url"] == "https://example.com/a"


def test_evidence_ingestion_is_idempotent(session):
    semantic = SemanticExtraction.model_validate(semantic_payload())
    _persist_semantics(session, "alpha", "run_one", EVIDENCE, semantic); session.commit()
    _persist_semantics(session, "alpha", "run_two", EVIDENCE, semantic); session.commit()
    from app.models import WorldShiftEvidenceORM
    assert session.scalar(select(func.count()).select_from(WorldShiftEvidenceORM)) == 1
    assert session.get(WorldShiftEvidenceORM, "ev_alpha").last_run_id == "run_two"
