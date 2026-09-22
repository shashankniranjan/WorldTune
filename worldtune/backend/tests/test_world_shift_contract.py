"""Tests for the GDELT-only frontend World Shift contract."""
from __future__ import annotations

from pathlib import Path

from app.schemas.world_shift import SnapshotMeta
from app.services.world_shift_contract import _compose


def _use_fixture(monkeypatch):
    monkeypatch.setenv(
        "WORLD_TUNE_SHIFTS_PATH",
        str(Path(__file__).parent / "fixtures" / "world_shifts.json"),
    )

def test_world_shift_contract_wrappers_are_snapshot_consistent(client, monkeypatch):
    _use_fixture(monkeypatch)
    listing = client.get("/world-shifts?limit=3")
    assert listing.status_code == 200
    list_body = listing.json()
    assert {"snapshotId", "generatedAt", "validUntil", "entries"} <= set(list_body)
    assert len(list_body["entries"]) == 3

    shift_id = list_body["entries"][0]["id"]
    snapshot_id = list_body["snapshotId"]
    detail = client.get(f"/world-shifts/{shift_id}?persona=tech&snapshotId={snapshot_id}")
    relationships = client.get(f"/world-shifts/{shift_id}/relationships?persona=tech&snapshotId={snapshot_id}")
    evidence = client.get(f"/world-shifts/{shift_id}/evidence?persona=tech&snapshotId={snapshot_id}")
    assert detail.status_code == relationships.status_code == evidence.status_code == 200

    detail_body = detail.json()
    assert detail_body["snapshotId"] == snapshot_id
    assert detail_body["schemaVersion"] == "2.0"
    assert 0 <= detail_body["shift"]["signalStrength"] <= 100
    assert detail_body["shift"]["status"] in {
        "surging", "rising", "changing", "watching", "stable", "declining", "elevated"
    }
    evidence_ids = {item["id"] for item in detail_body["evidence"]}
    assert all("imageUrl" in item for item in detail_body["evidence"])
    assert any(item["imageUrl"] is None for item in detail_body["evidence"])
    for item in detail_body["content"]["impact"]["directImpacts"]:
        assert set(item["evidenceIds"]) <= evidence_ids
    for node in detail_body["relationships"]["nodes"]:
        assert set(node["evidenceIds"]) <= evidence_ids
    assert detail_body["content"]["impact"]["impactChain"]
    assert detail_body["content"]["impact"]["secondOrderEffects"]
    assert detail_body["relationships"]["crossShiftLinks"]
    assert detail_body["relationships"]["personalPaths"]
    assert len(detail_body["whatHappensNext"]["scenarios"]) == 3

    assert relationships.json()["snapshotId"] == snapshot_id
    assert evidence.json()["snapshotId"] == snapshot_id


def test_world_shift_contract_rejects_stale_snapshot(client, monkeypatch):
    _use_fixture(monkeypatch)
    listing = client.get("/world-shifts").json()
    shift_id = listing["entries"][0]["id"]
    response = client.get(f"/world-shifts/{shift_id}?snapshotId=stale-snapshot")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "SNAPSHOT_MISMATCH"


def test_conflict_shift_is_a_sourced_briefing_not_a_topic_placeholder():
    row = {
        "date": "2026-09-20", "topic": "Armed Conflict and Military Escalation",
        "category": "geopolitics", "direction": "flat", "direction_label": "STABLE",
        "priority_score": 0.8, "evidence_article_count": 10, "evidence_unique_domains": 5,
        "organizations": "[]", "locations": "[]", "representative_evidence": "[]",
    }
    snapshot = _compose(row, [row], "finance", SnapshotMeta(
        snapshotId="test", generatedAt="2026-09-20T23:59:59Z", validUntil="2026-09-21T23:59:59Z",
    ))
    overview = snapshot.shift.overview
    assert overview.context_brief is not None
    assert "United States" in overview.context_brief.what_it_is
    assert len(overview.timeline) >= 5
    assert {actor.name for actor in overview.actors} >= {"United States", "Iran", "Israel", "Houthis / Ansar Allah", "Saudi Arabia"}
    assert any(item.image_url for item in snapshot.evidence)
    assert all(event.evidence_ids for event in overview.timeline)
    assert any("insurance" in item.summary.lower() for item in snapshot.content.impact.impact_chain)
    assert snapshot.content.domain["groups"][0].title == "Your finance & investing lens"
    finance_exposure = snapshot.content.impact.exposure_map
    assert {item.entity_name for item in finance_exposure} >= {
        "Lockheed Martin", "Bharat Electronics", "ONGC", "Indian Oil", "InterGlobe Aviation / IndiGo",
    }
    assert all(item.countries and item.horizons and item.reasoning for item in finance_exposure)

    tech = _compose(row, [row], "tech", SnapshotMeta(
        snapshotId="test", generatedAt="2026-09-20T23:59:59Z", validUntil="2026-09-21T23:59:59Z",
    ))
    tech_exposure = tech.content.impact.exposure_map
    assert {item.entity_name for item in tech_exposure} >= {
        "Palantir", "BlackSky", "Bharat Electronics", "ideaForge", "Zen Technologies",
    }
    assert all(item.opportunity_type for item in tech_exposure)


def test_world_shift_contract_supports_evidence_filters(client, monkeypatch):
    _use_fixture(monkeypatch)
    listing = client.get("/world-shifts").json()
    shift_id = listing["entries"][0]["id"]
    response = client.get(f"/world-shifts/{shift_id}/evidence?type=news&confidence=low&limit=2")
    assert response.status_code == 200
    assert len(response.json()["evidence"]) <= 2
    assert all(item["type"] == "news" and item["confidence"] == "low" for item in response.json()["evidence"])


def test_refresh_configuration_defaults_to_daily_and_persists(client):
    current = client.get("/world-shifts/refresh-configuration")
    assert current.status_code == 200
    assert current.json()["intervalSeconds"] == 86400
    changed = client.put("/world-shifts/refresh-configuration", json={
        "intervalSeconds": 43200, "webResearchEnabled": True, "webResultsPerShift": 3,
    })
    assert changed.status_code == 200
    assert changed.json()["intervalSeconds"] == 43200
    assert client.get("/world-shifts/refresh-configuration").json()["intervalSeconds"] == 43200


def test_refresh_configuration_rejects_unapproved_interval(client):
    response = client.put("/world-shifts/refresh-configuration", json={
        "intervalSeconds": 600, "webResearchEnabled": True, "webResultsPerShift": 3,
    })
    assert response.status_code == 422
