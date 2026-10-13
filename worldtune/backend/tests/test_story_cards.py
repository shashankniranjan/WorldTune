"""Story-card grounding: each card must cite real evidence, stay short, and avoid advice."""
from app.schemas.world_shift import StoryCard
from app.services.world_shift_ai import CARD_BODY_MAX, _card_ok, _cards

CORPUS = '{"evidence": "twelve people were killed, 12 killed"}'
IDS = {"e1", "e2"}


def card(key="happened", headline="Strike kills 12", body="12 people were killed.", ids=("e1",)):
    return StoryCard(key=key, headline=headline, body=body, evidenceIds=list(ids))


def test_grounded_card_passes():
    assert _card_ok(card(), CORPUS, IDS)


def test_unknown_evidence_id_rejected():
    assert not _card_ok(card(ids=("nope",)), CORPUS, IDS)


def test_invented_number_rejected_except_on_next_card():
    assert not _card_ok(card(body="Cost 99 million."), CORPUS, IDS)
    assert _card_ok(card(key="next", headline="Talks may restart", body="Could happen in 7 days."), CORPUS, IDS)


def test_advice_language_rejected_on_every_card():
    assert not _card_ok(card(key="next", body="Investors should buy oil."), CORPUS, IDS)


def test_overlong_body_rejected():
    assert not _card_ok(card(body="word " * (CARD_BODY_MAX // 4)), CORPUS, IDS)


def test_cards_dedupe_and_respect_allowed_keys():
    out = _cards([card(), card(), card(key="you")], CORPUS, IDS, {"happened", "why", "next"})
    assert [c.key for c in out] == ["happened"]


def test_event_ids_cited_as_evidence_are_repaired_to_their_evidence_ids():
    from app.schemas.world_shift import AIEvent, SemanticExtraction, WorldShiftSynthesis
    from app.services.world_shift_ai import repair_evidence_ids
    semantic = SemanticExtraction(events=[AIEvent(eventId="t:ev_x", title="x", summary="y", evidenceIds=["ev_1", "ev_2"],
                                                  entityIds=[], evidenceClass="observed")], claims=[], entities=[], relationships=[])
    out = WorldShiftSynthesis.model_validate({
        "summary": "s", "quickTake": "q", "keyThemes": [], "relationshipStory": {},
        "whatsHappening": [{"text": "a", "evidenceClass": "observed", "evidenceIds": ["t:ev_x", "ev_1"]}],
        "whyItMatters": [], "keyDevelopments": [], "watchNext": [],
        "storyCards": [{"key": "happened", "headline": "h", "body": "b", "evidenceIds": ["t:ev_x"]}]})
    fixed = repair_evidence_ids(out, {"ev_1", "ev_2"}, semantic)
    assert fixed.whats_happening[0].evidence_ids == ["ev_1", "ev_2"]
    assert fixed.story_cards[0].evidence_ids == ["ev_1", "ev_2"]


def test_impact_with_causal_mechanism_is_dropped_not_stage_failing():
    from app.schemas.world_shift import PersonaSynthesis
    from app.services.world_shift_ai import filter_invalid_objects
    item = lambda i, mech: {"id": i, "title": "t", "summary": "s", "evidenceIds": ["ev_1"], "evidenceClass": "observed",
                             "mechanism": mech, "direction": "mixed", "magnitude": "low", "claimIds": []}
    out = PersonaSynthesis.model_validate({
        "summary": "s", "domainGroups": [], "risks": [], "opportunities": [], "watchItems": [],
        "directImpacts": [item("a", "Demand drives prices up"), item("b", "Reported by two outlets")]})
    filtered, removed = filter_invalid_objects(out, [{"evidenceId": "ev_1"}], None)
    assert [i.id for i in filtered.direct_impacts] == ["b"] and removed == 1
