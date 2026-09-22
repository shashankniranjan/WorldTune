"""Every World Shift is held to the reference shift's quality bar.

These tests exist because the failure mode here is silent: a shift renders
without error while being far thinner than the reference, or a heading written
for one shift appears on another. Both are asserted against directly.
"""
from __future__ import annotations

import re

import pytest

from app.services.world_shift_contract import list_contract_shifts, get_contract_shift
from app.services.world_shift_editorial import CONFLICT_ID
from app.services.shift_knowledge import PACKS, knowledge_for

PERSONAS = ("finance", "tech")


@pytest.fixture(scope="module")
def shift_ids() -> list[str]:
    return [entry.id for entry in list_contract_shifts().entries]


@pytest.fixture(scope="module")
def snapshots(shift_ids) -> dict[tuple[str, str], object]:
    return {(shift, persona): get_contract_shift(shift, persona)
            for shift in shift_ids for persona in PERSONAS}


def _others(shift_ids):
    return [shift for shift in shift_ids if shift != CONFLICT_ID]


class TestDepth:
    """Minimum structure, measured against what the reference shift carries."""

    def test_every_shift_and_persona_has_substantive_impact(self, snapshots, shift_ids):
        for shift in _others(shift_ids):
            for persona in PERSONAS:
                impact = snapshots[(shift, persona)].content.impact
                claims = (impact.direct_impacts + impact.impact_chain + impact.second_order_effects
                          + impact.opportunities + impact.risks + impact.watch_items)
                assert len(claims) >= 8, f"{shift}/{persona} has only {len(claims)} claims"
                assert len(impact.exposure_map) >= 4, f"{shift}/{persona} exposure map is thin"
                assert impact.summary and len(impact.summary) > 120

    def test_every_claim_states_a_mechanism_and_cites_evidence(self, snapshots, shift_ids):
        for shift in _others(shift_ids):
            for persona in PERSONAS:
                impact = snapshots[(shift, persona)].content.impact
                for claim in (impact.direct_impacts + impact.impact_chain
                              + impact.second_order_effects + impact.risks):
                    assert claim.mechanism, f"{shift}/{persona}: {claim.title} has no mechanism"
                    assert claim.evidence_ids, f"{shift}/{persona}: {claim.title} cites nothing"

    def test_every_exposure_shows_its_reasoning(self, snapshots, shift_ids):
        for shift in _others(shift_ids):
            for persona in PERSONAS:
                for exposure in snapshots[(shift, persona)].content.impact.exposure_map:
                    assert len(exposure.reasoning) >= 3, f"{shift}/{persona}: {exposure.entity_name}"
                    assert exposure.verification_hint
                    assert exposure.evidence_class == "reasoned"

    def test_overview_is_a_briefing_not_a_stub(self, snapshots, shift_ids):
        for shift in _others(shift_ids):
            overview = snapshots[(shift, "finance")].shift.overview
            assert overview.context_brief is not None
            assert len(overview.timeline) >= 3, f"{shift} timeline is thin"
            assert len(overview.actors) >= 4, f"{shift} names too few actors"
            assert len(overview.facts_and_figures) >= 2
            assert len(overview.drivers) >= 3
            assert len(overview.contradictions) >= 2

    def test_relationships_explain_a_system(self, snapshots, shift_ids):
        for shift in _others(shift_ids):
            relationships = snapshots[(shift, "tech")].relationships
            assert len(relationships.nodes) >= 5, f"{shift} relationship graph is thin"
            directions = {edge.category for edge in relationships.edges}
            assert {"upstream", "downstream"} <= directions, (
                f"{shift} does not distinguish what caused it from what it affects"
            )
            for edge in relationships.edges:
                assert edge.mechanism, f"{shift}: edge {edge.id} has no mechanism"

    def test_scenarios_are_present_and_actionable(self, snapshots, shift_ids):
        for shift in _others(shift_ids):
            for persona in PERSONAS:
                forecast = snapshots[(shift, persona)].what_happens_next
                assert len(forecast.scenarios) == 3
                assert {s.label for s in forecast.scenarios} == {"base", "upside", "downside"}
                for scenario in forecast.scenarios:
                    assert scenario.indicators and scenario.invalidators

    def test_evidence_is_traceable(self, snapshots, shift_ids):
        for shift in _others(shift_ids):
            snapshot = snapshots[(shift, "finance")]
            assert len(snapshot.evidence) >= 10, f"{shift} has too little evidence"
            for item in snapshot.evidence:
                assert item.url.startswith("http")
                assert item.source

    def test_no_claim_cites_an_evidence_id_that_does_not_exist(self, snapshots, shift_ids):
        for shift in shift_ids:
            for persona in PERSONAS:
                snapshot = snapshots[(shift, persona)]
                known = {item.id for item in snapshot.evidence}
                supported = {target for item in snapshot.evidence for target in item.supports}
                impact = snapshot.content.impact
                cited: set[str] = set()
                for claim in (impact.direct_impacts + impact.impact_chain
                              + impact.second_order_effects + impact.opportunities
                              + impact.risks + impact.watch_items):
                    cited.update(claim.evidence_ids)
                for scenario in snapshot.what_happens_next.scenarios:
                    cited.update(scenario.evidence_ids)
                dangling = cited - known - supported
                assert not dangling, f"{shift}/{persona} cites unknown evidence: {sorted(dangling)[:3]}"


class TestPersonaSeparation:
    def test_personas_are_not_rewrites_of_each_other(self, snapshots, shift_ids):
        for shift in _others(shift_ids):
            titles = {}
            for persona in PERSONAS:
                impact = snapshots[(shift, persona)].content.impact
                titles[persona] = {claim.title for claim in
                                   (impact.direct_impacts + impact.impact_chain
                                    + impact.second_order_effects + impact.opportunities
                                    + impact.risks + impact.watch_items)}
            shared = titles["finance"] & titles["tech"]
            assert not shared, f"{shift} reuses claim titles across personas: {sorted(shared)[:2]}"

    def test_persona_headings_differ_and_describe_the_persona(self, snapshots, shift_ids):
        for shift in _others(shift_ids):
            finance = snapshots[(shift, "finance")].content.impact
            tech = snapshots[(shift, "tech")].content.impact
            assert finance.headline and tech.headline
            assert finance.headline != tech.headline
            assert finance.exposure_headline != tech.exposure_headline
            assert finance.lens_title != tech.lens_title

    def test_lens_groups_are_persona_specific(self, snapshots, shift_ids):
        for shift in _others(shift_ids):
            groups = {persona: {group.title for group in
                                snapshots[(shift, persona)].content.domain["groups"]}
                      for persona in PERSONAS}
            # The observed-entity group is shared by construction; the
            # interpretive groups must not be.
            interpretive = {persona: {title for title in titles
                                      if "named in the reporting" not in title}
                            for persona, titles in groups.items()}
            assert not (interpretive["finance"] & interpretive["tech"]), shift


class TestHeadingsAndLeakage:
    CONFLICT_WORDING = re.compile(
        r"hormuz|bab el|houthi|interceptor|escalation unfolded|de-escalation|"
        r"lockheed|missile|ceasefire", re.I)

    def test_reference_wording_does_not_appear_in_other_shifts(self, snapshots, shift_ids):
        for shift in _others(shift_ids):
            for persona in PERSONAS:
                snapshot = snapshots[(shift, persona)]
                # Cross-shift links legitimately name the conflict shift; the
                # test targets the shift's own analysis instead.
                text = " ".join([
                    snapshot.shift.overview.what_happened,
                    snapshot.shift.overview.why_it_matters,
                    snapshot.content.impact.summary,
                    snapshot.content.impact.headline or "",
                    snapshot.content.impact.exposure_blurb or "",
                    snapshot.shift.overview.timeline_heading or "",
                ] + [claim.summary for claim in snapshot.content.impact.direct_impacts])
                found = self.CONFLICT_WORDING.findall(text)
                assert not found, f"{shift}/{persona} contains reference wording: {found}"

    def test_every_shift_supplies_its_own_section_headings(self, snapshots, shift_ids):
        headings: dict[str, str] = {}
        for shift in _others(shift_ids):
            overview = snapshots[(shift, "finance")].shift.overview
            assert overview.timeline_heading and overview.timeline_kicker
            assert shift not in headings
            headings[shift] = overview.timeline_heading
        assert len(set(headings.values())) == len(headings), "timeline headings are duplicated"

    def test_no_provider_terminology_reaches_the_reader(self, snapshots, shift_ids):
        forbidden = re.compile(r"\bgdelt\b|\bgkg\b|silver_articles|parquet", re.I)
        for shift in _others(shift_ids):
            for persona in PERSONAS:
                snapshot = snapshots[(shift, persona)]
                blob = snapshot.model_dump_json()
                found = forbidden.findall(blob)
                assert not found, f"{shift}/{persona} exposes provider terminology: {set(found)}"

    def test_no_empty_or_placeholder_sections(self, snapshots, shift_ids):
        for shift in _others(shift_ids):
            for persona in PERSONAS:
                snapshot = snapshots[(shift, persona)]
                groups = snapshot.content.domain["groups"]
                assert groups, f"{shift}/{persona} has no lens groups"
                for group in groups:
                    assert group.items, f"{shift}/{persona}: empty group {group.title}"
                    for item in group.items:
                        assert item.summary.strip()


class TestReferenceIsUnchanged:
    """The golden reference must keep serving its editorial content."""

    def test_reference_still_uses_the_editorial_path(self, snapshots):
        for persona in PERSONAS:
            snapshot = snapshots[(CONFLICT_ID, persona)]
            assert snapshot.shift.overview.actors, "reference lost its actor briefing"
            assert snapshot.shift.overview.facts_and_figures
            assert len(snapshot.content.impact.exposure_map) >= 5
            # The editorial bundle's curated records are the reference's spine.
            assert any(item.id.startswith(f"{CONFLICT_ID}:brief:") for item in snapshot.evidence)

    def test_reference_keeps_its_original_heading_fallbacks(self, snapshots):
        # The reference does not supply headings, so the frontend keeps
        # rendering the wording it always has.
        overview = snapshots[(CONFLICT_ID, "finance")].shift.overview
        assert overview.timeline_heading is None
        assert overview.timeline_kicker is None
        assert snapshots[(CONFLICT_ID, "finance")].content.impact.headline is None


class TestKnowledgeLayer:
    def test_packs_do_not_share_prose_between_personas(self):
        for slug, pack in PACKS.items():
            assert pack.finance.summary != pack.tech.summary, slug
            assert pack.finance.lens_blurb != pack.tech.lens_blurb, slug

    def test_a_shift_without_a_pack_still_renders(self):
        pack = knowledge_for("quantum-computing", "Quantum Computing", "technology")
        assert pack.finance.scenarios and pack.tech.scenarios
        assert pack.finance.headline != pack.tech.headline
        assert "Quantum Computing" in pack.what_it_is

    def test_packs_name_downstream_shifts_that_exist(self, shift_ids):
        known = set(shift_ids) | set(PACKS)
        for slug, pack in PACKS.items():
            for link in pack.downstream:
                if link.shift_slug:
                    assert link.shift_slug in known, f"{slug} links to unknown shift {link.shift_slug}"
