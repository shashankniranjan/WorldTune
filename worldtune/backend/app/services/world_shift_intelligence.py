"""Compose a full World Shift briefing from evidence plus domain knowledge.

This is the shared path for every shift. It takes three inputs -- the ranked
signal row, the per-shift source artifact built by
``scripts/build_shift_intelligence.py``, and the declarative knowledge pack --
and produces the complete frontend contract for either persona.

The division of labour matters:

* the artifact supplies everything time-bound and observable (which publishers
  reported what, when attention moved, which entities recur),
* the knowledge pack supplies everything durable and interpretive (mechanisms,
  actors, exposure reasoning, scenarios),
* this module joins them, attaches evidence identifiers to individual claims,
  and applies the persona selection.

Nothing here is shift-specific. Adding a shift means adding a knowledge pack.

Provider terminology never appears in composed output: a reader sees publisher
names and dates, which is the attribution that actually matters to them.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.schemas.world_shift import (
    ActorBrief,
    ContextBrief,
    CrossShiftLink,
    DomainEntity,
    DomainGroup,
    Evidence,
    FactFigure,
    Impact,
    ImpactItem,
    ExposureItem,
    IntelligencePoint,
    Overview,
    PersonalPath,
    RelationshipEdge,
    RelationshipNode,
    Relationships,
    Scenario,
    TimelineEvent,
    WhatHappensNext,
)
from app.services.shift_knowledge import KnowledgePack, knowledge_for
from app.services.shift_knowledge.base import Claim, Exposure

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_ARTIFACT = ROOT / "data/processed/worldtune/world_shifts/shift_intelligence.json"

# How many source records back a single claim. Enough for the reader to check
# the claim against more than one publisher, few enough to stay reviewable.
CLAIM_EVIDENCE = 4


def _artifact_path() -> Path:
    return Path(os.environ.get("WORLD_TUNE_INTELLIGENCE_PATH", str(DEFAULT_ARTIFACT)))


@lru_cache(maxsize=4)
def _load_artifact(path_text: str, mtime_ns: int, size: int) -> dict[str, Any]:
    del mtime_ns, size
    path = Path(path_text)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (ValueError, OSError):
        return {}


def artifact_for(slug: str) -> dict[str, Any]:
    path = _artifact_path()
    try:
        stat = path.stat()
    except OSError:
        return {}
    return _load_artifact(str(path), stat.st_mtime_ns, stat.st_size).get(slug, {})


def has_intelligence(slug: str) -> bool:
    return bool(artifact_for(slug).get("evidence"))


# --------------------------------------------------------------------------
# entity and evidence helpers
# --------------------------------------------------------------------------

def _shorten_place(value: str) -> str:
    """``Seoul, Soul-T'ukpyolsi, South Korea`` -> ``Seoul, South Korea``."""
    parts = [part.strip() for part in value.split(",") if part.strip()]
    if len(parts) <= 2:
        return ", ".join(parts)
    if parts[0].lower() == parts[1].lower():
        return ", ".join([parts[0], parts[-1]])
    return f"{parts[0]}, {parts[-1]}"


def _clean_entities(values: list[str], limit: int) -> list[str]:
    """Deduplicate the entity rollup into names a reader would recognise."""
    seen: dict[str, str] = {}
    for raw in values:
        name = _shorten_place(str(raw).strip())
        if len(name) < 3 or name.isdigit():
            continue
        # Collapse demonyms onto the place: "Russian" and "Russia" are one entity
        # to a reader even though they are two strings in the source records.
        key = re.sub(r"(ian|ese|ish|an|n)$", "", name.split(",")[0].lower())
        if len(key) < 3:
            key = name.lower()
        if key in seen:
            # Prefer the longer, more specific rendering.
            if len(name) > len(seen[key]):
                seen[key] = name
            continue
        seen[key] = name
    return list(seen.values())[:limit]


_SOURCE_TIERS = {0: "primary", 1: "secondary", 2: "secondary", 3: "aggregator"}


def build_evidence(slug: str, artifact: dict[str, Any], fallback_date: str) -> list[Evidence]:
    """Turn the artifact's source records into contract evidence.

    Titles were recovered from the publisher URL where the source record had
    none; that provenance is stated in the summary rather than hidden, because
    a recovered headline is not the same as a publisher-supplied one.
    """
    records = artifact.get("evidence") or []
    domains = [item.get("domain", "") for item in records]
    result: list[Evidence] = []
    for index, record in enumerate(records):
        url = str(record.get("url") or "")
        if not url.startswith(("http://", "https://")):
            continue
        domain = str(record.get("domain") or "").strip()
        published = str(record.get("publishedAt") or "").strip()
        published = (published.replace(" ", "T")[:19] + "Z") if len(published) >= 10 else fallback_date
        tier = int(record.get("tier", 2))
        themes = [str(theme) for theme in (record.get("themes") or [])][:3]
        result.append(Evidence(
            id=f"{slug}:e{index + 1}",
            type="news",
            source=domain,
            title=str(record.get("title") or "").strip() or f"Report from {domain}",
            summary=(
                f"Published by {domain}. The headline shown is recovered from the article address "
                f"because the source record carried no title; open the original for the publisher's "
                f"own wording and full context."
            ),
            publishedAt=published,
            url=url,
            imageUrl=None,
            entities=_clean_entities(list(artifact.get("organizations") or []), 5),
            tags=[theme for theme in themes] + [str(artifact.get("category", "world")).replace("_", " ")],
            relationshipRole="supports the reported development",
            confidence="medium" if tier <= 1 else "low",
            supports=[f"{slug}:node"],
            sourceDomain=domain,
            originalHeadline=str(record.get("title") or "").strip() or None,
            sourceSnippet=None,
            evidenceClass="observed",
            sourceClass=_SOURCE_TIERS.get(tier, "unknown"),
            retrievalStatus="metadata_only",
            publisherFamily=domain,
            independentPublisherCount=max(1, len(set(domains))),
            corroborationStatus=(
                "independently_corroborated" if len(set(domains)) >= 5 else "single_source"
            ),
        ))
    return result


def _ids(evidence: list[Evidence], start: int = 0, count: int = CLAIM_EVIDENCE) -> list[str]:
    """A rotating window of evidence ids.

    Rotating rather than always using the first few records means different
    claims cite different publishers, so the evidence drawer is useful instead
    of showing the same four items for everything on the page.
    """
    if not evidence:
        return []
    ids = [item.id for item in evidence]
    start = start % len(ids)
    return [ids[(start + offset) % len(ids)] for offset in range(min(count, len(ids)))]


def _short_label(text: str, words: int = 7) -> str:
    """A node label short enough to read inside a graph node and an edge heading."""
    cleaned = re.split(r"[—:;,.]", text.strip())[0].strip()
    parts = cleaned.split()
    return " ".join(parts[:words]) + ("…" if len(parts) > words else "")


def _hero_evidence(slug: str, pack: KnowledgePack, published: str) -> Evidence | None:
    """A single illustrative image record, clearly labelled as illustrative.

    The source corpus carries no images. Rather than leaving every shift
    without one or borrowing an unrelated shift's picture, each pack names a
    subject-appropriate public-domain or freely licensed image and this record
    says plainly that it illustrates the subject rather than an event.
    """
    if pack.hero is None:
        return None
    return Evidence(
        id=f"{slug}:illustration",
        type="illustration",
        source=pack.hero.credit,
        title=f"{pack.subject[:1].upper()}{pack.subject[1:]}",
        summary=f"{pack.hero.caption} This image illustrates the subject; it does not depict a reported event.",
        publishedAt=published,
        url=pack.hero.url,
        imageUrl=pack.hero.url,
        entities=[],
        tags=["illustration", "subject context"],
        relationshipRole="illustrates the subject of this shift",
        confidence="low",
        supports=[f"{slug}:node"],
        sourceDomain="commons.wikimedia.org",
        evidenceClass="associated",
        sourceClass="unknown",
        retrievalStatus="complete",
        publisherFamily=pack.hero.credit,
        independentPublisherCount=1,
        corroborationStatus="single_source",
    )


# --------------------------------------------------------------------------
# claim and exposure mapping
# --------------------------------------------------------------------------

def _claim_item(slug: str, prefix: str, index: int, claim: Claim,
                evidence: list[Evidence], offset: int) -> ImpactItem:
    return ImpactItem(
        id=f"{slug}:{prefix}:{index}",
        title=claim.title,
        summary=claim.summary,
        direction=claim.direction,
        magnitude=claim.magnitude,
        evidenceIds=_ids(evidence, offset),
        evidenceClass="inferred",
        mechanism=claim.mechanism,
        horizon=claim.horizon,
        confidence=claim.confidence,
        invalidators=list(claim.invalidators),
    )


def _claims(slug: str, prefix: str, claims: tuple[Claim, ...],
            evidence: list[Evidence], offset: int) -> list[ImpactItem]:
    return [_claim_item(slug, prefix, index, claim, evidence, offset + index * 2)
            for index, claim in enumerate(claims, start=1)]


def _exposure_item(slug: str, exposure: Exposure, evidence: list[Evidence], offset: int) -> ExposureItem:
    ids = _ids(evidence, offset, 3)
    return ExposureItem(
        id=f"{slug}:exposure:{exposure.key}",
        entityName=exposure.name,
        ticker=exposure.ticker,
        direction=exposure.direction,
        ring=exposure.ring,
        mechanism=exposure.mechanism,
        reasoning=list(exposure.reasoning),
        confidence=exposure.confidence,
        derivedFrom=ids,
        verificationHint=exposure.verify,
        evidenceIds=ids,
        evidenceClass="reasoned",
        horizons=list(exposure.horizons),
        countries=list(exposure.countries),
        opportunityType=exposure.opportunity_type,
    )


def build_impact(slug: str, pack: KnowledgePack, persona: str, evidence: list[Evidence]) -> Impact:
    side = pack.persona(persona)
    return Impact(
        summary=side.summary,
        directImpacts=_claims(slug, "direct", side.direct, evidence, 0),
        impactChain=_claims(slug, "chain", side.chain, evidence, 3),
        secondOrderEffects=_claims(slug, "second", side.second_order, evidence, 7),
        opportunities=_claims(slug, "opportunity", side.opportunities, evidence, 10),
        risks=_claims(slug, "risk", side.risks, evidence, 13),
        watchItems=_claims(slug, "watch", side.watch, evidence, 16),
        exposureMap=[_exposure_item(slug, exposure, evidence, 2 + index * 3)
                     for index, exposure in enumerate(side.exposures)],
        kicker=side.kicker,
        headline=side.headline,
        exposureHeadline=side.exposure_headline,
        exposureBlurb=side.exposure_blurb,
        lensTitle=side.lens_title,
        lensBlurb=side.lens_blurb,
    )


def build_domain_groups(slug: str, pack: KnowledgePack, persona: str,
                        evidence: list[Evidence], artifact: dict[str, Any]) -> list[DomainGroup]:
    """The persona "Your lens" tab: interpretive groups plus observed entities."""
    side = pack.persona(persona)
    groups: list[DomainGroup] = []
    for group_index, group in enumerate(side.lens_groups, start=1):
        groups.append(DomainGroup(
            id=f"{slug}:{persona}:lens:{group_index}",
            title=group.title,
            entityType=group.entity_type,
            items=[DomainEntity(
                id=f"{slug}:{persona}:lens:{group_index}:{item_index}",
                name=name,
                type=group.entity_type,
                direction=direction,
                magnitude="medium",
                summary=summary,
                evidenceIds=_ids(evidence, group_index * 5 + item_index),
            ) for item_index, (name, direction, summary) in enumerate(group.items, start=1)],
        ))
    entities = _clean_entities(list(artifact.get("organizations") or []), 8)
    if entities:
        groups.append(DomainGroup(
            id=f"{slug}:{persona}:entities",
            title="Countries and organisations named in the reporting",
            entityType="observed_entity",
            items=[DomainEntity(
                id=f"{slug}:entity:{re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')}",
                name=name,
                type="observed_entity",
                direction="uncertain",
                magnitude="low",
                summary=(
                    "Recurs across the source records for this shift. Being named in coverage "
                    "indicates involvement in the story, not a measured market or career effect."
                ),
                evidenceIds=_ids(evidence, index * 2, 3),
            ) for index, name in enumerate(entities)],
        ))
    return groups


# --------------------------------------------------------------------------
# overview
# --------------------------------------------------------------------------

def _points(texts: list[str], evidence: list[Evidence], offset: int,
            evidence_class: str = "inferred") -> list[IntelligencePoint]:
    return [IntelligencePoint(
        text=text, evidenceClass=evidence_class, evidenceIds=_ids(evidence, offset + index * 3),
    ) for index, text in enumerate(texts) if text]


def _attention_sentence(artifact: dict[str, Any], status: str) -> str:
    articles = int(artifact.get("articleCount") or 0)
    domains = int(artifact.get("domainCount") or 0)
    window = int(artifact.get("windowDomainCount") or 0)
    if not articles:
        return ""
    return (
        f"On the day covered here, {articles} reports from {domains} independent publishers matched "
        f"this subject, out of {window} publishers that have covered it over the past two weeks. "
        f"The attention signal is {status}, which describes coverage rather than any measured "
        f"real-world change."
    )


def build_overview(slug: str, pack: KnowledgePack, artifact: dict[str, Any],
                   evidence: list[Evidence], status: str) -> Overview:
    attention = _attention_sentence(artifact, status)
    dated = sorted([item for item in evidence if item.type == "news"],
                   key=lambda item: item.published_at or "")
    earliest = dated[0] if dated else None
    # Best-sourced record, used where the point is "here is the reporting"
    # rather than "here is the chronology".
    best = min(dated, key=lambda item: (0 if item.source_class == "primary" else 1,
                                        -len(item.title))) if dated else None
    window_start = str(artifact.get("windowStart") or "")
    single_day = bool(dated) and earliest.published_at[:10] == dated[-1].published_at[:10]

    origin = (
        (f"The source records collected for this shift all come from "
         f"{earliest.published_at[:10]}, so they show the current state of the reporting rather than "
         f"how it began. " if single_day and earliest else
         f"The source records collected for this shift run from {earliest.published_at[:10]} onward, "
         f"which is where this evidence window opens rather than where the wider issue began. "
         if earliest else "")
        + ("Attention has been tracked since "
           f"{window_start}. " if window_start else "")
        + "What produced a shift of this kind, in general terms: "
        + " ".join(pack.causes[:2])
    )
    context = ContextBrief(
        whatItIs=pack.what_it_is,
        howItStarted=origin,
        latest=(
            (f"A representative report in this window is “{best.title}” ({best.source}, "
             f"{best.published_at[:10]}). " if best else "")
            + attention
        ),
        whatItIsEvidenceIds=_ids(evidence, 0, 3),
        howItStartedEvidenceIds=_ids(evidence, 4, 2),
        latestEvidenceIds=[best.id] if best else _ids(evidence, 8, 2),
    )

    timeline: list[Any] = []
    notable = artifact.get("notableDays") or []
    by_date: dict[str, list[Evidence]] = {}
    for item in dated:
        by_date.setdefault(item.published_at[:10], []).append(item)
    for day in notable[-6:]:
        date = str(day.get("date"))
        same_day = by_date.get(date, [])
        # Reports published that day, from the artifact where the evidence set
        # itself does not reach back that far.
        day_reports = [str(report.get("title") or "").strip()
                       for report in (day.get("topReports") or [])]
        day_sources = [str(report.get("domain") or "").strip()
                       for report in (day.get("topReports") or [])]
        change = float(day.get("changeVsAverage") or 0)
        direction = "above" if change >= 0 else "below"
        headline = same_day[0].title if same_day else (day_reports[0] if day_reports else None)
        source = same_day[0].source if same_day else (day_sources[0] if day_sources else None)
        others = day_reports[1:3] if not same_day else [item.title for item in same_day[1:3]]
        summary_parts = []
        if source:
            summary_parts.append(f"Reported by {source}.")
        if others:
            summary_parts.append("Also published that day: " + "; ".join(f"“{title}”" for title in others) + ".")
        summary_parts.append(
            f"{day.get('articles')} reports from {day.get('domains')} publishers, "
            f"{abs(round(change * 100))}% {direction} the two-week average for this subject."
        )
        timeline.append(dict(
            date=date,
            title=headline or f"Coverage {direction} the two-week average",
            summary=" ".join(summary_parts),
            status="reported",
            evidenceIds=[item.id for item in same_day[:3]] or _ids(evidence, 0, 2),
        ))
    if not timeline:
        timeline = [dict(
            date=item.published_at[:10], title=item.title,
            summary=f"Reported by {item.source}. Open the original for the publisher's full account.",
            status="reported", evidenceIds=[item.id],
        ) for item in dated[-5:]]

    facts: list[FactFigure] = []
    if artifact.get("articleCount"):
        facts.append(FactFigure(
            value=str(artifact["articleCount"]), label="reports on the day covered",
            context="Counted across independent publishers matching this subject. A measure of attention, not of impact.",
            evidenceIds=_ids(evidence, 0, 3),
        ))
    if artifact.get("windowDomainCount"):
        facts.append(FactFigure(
            value=str(artifact["windowDomainCount"]), label="publishers over two weeks",
            context="Distinct publishers that have covered this subject in the evidence window. Breadth of coverage, not corroboration of any single claim.",
            evidenceIds=_ids(evidence, 5, 3),
        ))
    if notable:
        peak = max(notable, key=lambda day: day.get("articles", 0))
        facts.append(FactFigure(
            value=str(peak.get("date")), label="busiest day in the window",
            context=f"{peak.get('articles')} reports from {peak.get('domains')} publishers. Peak attention, which may or may not coincide with the most consequential development.",
            evidenceIds=_ids(evidence, 9, 3),
        ))

    actors = [ActorBrief(
        name=actor.name, role=actor.role, position=actor.position, status="reported",
        evidenceIds=_ids(evidence, index * 4, 3),
    ) for index, actor in enumerate(pack.actors)]

    themes = _clean_entities(list(artifact.get("themes") or []), 6)
    return Overview(
        whatHappened=pack.what_it_is,
        whyItMatters=pack.why_it_matters,
        quickTake=pack.system_framing,
        characteristics=[f"{status.title()} attention signal", "Evidence-linked interpretation",
                         "Mechanism stated, not assumed"],
        themes=list(pack.themes) + themes,
        whatsHappening=_points(
            [f"Coverage in this window centres on reports such as “{best.title}” ({best.source}) "
             f"and “{dated[1].title}” ({dated[1].source})." if best and len(dated) > 1
             else (f"Coverage in this window centres on “{best.title}” ({best.source})." if best else ""),
             f"The subject in scope is {pack.subject}. {pack.system_framing}",
             f"Recurring in the reporting: {', '.join(_clean_entities(list(artifact.get('organizations') or []), 5))}."
             if artifact.get("organizations") else ""],
            evidence, 0, "observed"),
        whyItMattersPoints=_points([pack.why_it_matters] + list(pack.causes[:2]), evidence, 6),
        keyDevelopments=_points(
            [f"{event['date']}: {event['title']}" for event in timeline[-4:]
             if not event["title"].startswith("Coverage ")]
            or [f"{item.published_at[:10]}: {item.title} ({item.source})" for item in dated[:4]],
            evidence, 12, "observed"),
        drivers=_points(list(pack.drivers), evidence, 4),
        watchNext=_points(
            [f"Indicators worth following: {', '.join(pack.indicators[:3])}.",
             f"And: {', '.join(pack.indicators[3:])}." if len(pack.indicators) > 3 else ""],
            evidence, 14),
        contradictions=_points(list(pack.uncertainty), evidence, 9),
        contextBrief=context,
        timeline=[TimelineEvent.model_validate(event) for event in timeline],
        actors=actors,
        factsAndFigures=facts,
        timelineKicker=pack.timeline_kicker,
        timelineHeading=pack.timeline_heading,
    )


# --------------------------------------------------------------------------
# relationships
# --------------------------------------------------------------------------

def build_relationships(slug: str, pack: KnowledgePack, persona: str, evidence: list[Evidence],
                        peers: list[tuple[str, str]], observed_at: str, updated_at: str) -> Relationships:
    """A causal system rather than a list of related topics.

    Three kinds of edge are produced, and they are labelled differently
    because they carry different warrant: what produced the shift (inferred
    from domain knowledge), what it transmits to (the pack's downstream
    model), and which other live shifts it shares evidence with (association
    only).
    """
    side = pack.persona(persona)
    topic_node = RelationshipNode(
        id=f"{slug}:node", label=pack.subject[:1].upper() + pack.subject[1:], type="world_shift",
        category="observed", summary=pack.what_it_is[:280],
        direction="uncertain", magnitude="high", evidenceIds=_ids(evidence, 0, 5),
    )
    nodes = [topic_node]
    edges: list[RelationshipEdge] = []

    for index, cause in enumerate(pack.causes, start=1):
        node_id = f"{slug}:cause:{index}"
        nodes.append(RelationshipNode(
            id=node_id, label=_short_label(cause), type="driver", category="inferred",
            summary=cause, direction="uncertain", magnitude="medium",
            evidenceIds=_ids(evidence, index * 3, 3),
        ))
        edges.append(RelationshipEdge(
            id=f"{slug}:edge:cause:{index}", source=node_id, target=topic_node.id,
            relationship="contributes_to", category="upstream", explanation=cause,
            confidence="medium", evidenceIds=_ids(evidence, index * 3, 3), evidenceClass="inferred",
            mechanism=cause, temporalOrder="precedes the current reporting",
            alternativeExplanations=[
                "Coverage may reflect editorial attention rather than a change in this driver",
            ],
            firstObservedAt=observed_at, lastUpdatedAt=updated_at,
        ))

    for index, link in enumerate(pack.downstream, start=1):
        node_id = f"{link.shift_slug}:node" if link.shift_slug else f"{slug}:downstream:{index}"
        nodes.append(RelationshipNode(
            id=node_id, label=link.title, type="world_shift" if link.shift_slug else "system",
            category="inferred", summary=link.explanation, direction="uncertain", magnitude="medium",
            evidenceIds=_ids(evidence, index * 4, 3),
        ))
        edges.append(RelationshipEdge(
            id=f"{slug}:edge:downstream:{index}", source=topic_node.id, target=node_id,
            relationship=link.relationship.replace(" ", "_"), category="downstream",
            explanation=link.explanation, confidence=link.confidence,
            evidenceIds=_ids(evidence, index * 4, 3), evidenceClass="inferred",
            mechanism=link.mechanism, temporalOrder="follows the current development",
            alternativeExplanations=[
                "Both may respond to a common cause rather than one driving the other",
            ],
            firstObservedAt=observed_at, lastUpdatedAt=updated_at,
        ))

    cross = [CrossShiftLink(
        shiftId=peer_slug, title=peer_title,
        relationship=next((link.relationship.replace(" ", "_") for link in pack.downstream
                           if link.shift_slug == peer_slug), "shares_drivers"),
        explanation=next((link.explanation for link in pack.downstream if link.shift_slug == peer_slug),
                         f"{peer_title} is being reported in the same window and shares entities or "
                         f"drivers with this shift. That is an association, not a causal link."),
        confidence="medium" if any(link.shift_slug == peer_slug for link in pack.downstream) else "low",
        evidenceClass="inferred" if any(link.shift_slug == peer_slug for link in pack.downstream) else "associated",
        evidenceIds=_ids(evidence, index * 5, 3),
        indicators=list(next((link.indicators for link in pack.downstream
                              if link.shift_slug == peer_slug), ()) or
                        ("shared entities", "shared publishers", "temporal ordering")),
    ) for index, (peer_slug, peer_title) in enumerate(peers[:4])]

    return Relationships(
        nodes=nodes, edges=edges,
        story={
            "why": (f"This shift is modelled as a system: {pack.system_framing}"),
            "direction": (
                "Upstream edges are what domain knowledge says produces a shift like this. "
                "Downstream edges are where it would transmit if it develops. Neither is a measured "
                "causal finding, and both are labelled as inference."
            ),
            "personaImpact": (
                f"The {'finance and investing' if persona == 'finance' else 'technology and career'} "
                f"reading follows one path through that system: {side.path_explanation}"
            ),
            "uncertainty": pack.uncertainty[0] if pack.uncertainty else None,
        },
        crossShiftLinks=cross,
        personalPaths=[PersonalPath(
            id=f"{slug}:path:{persona}", title=side.path_title, persona=persona,
            steps=list(side.path_steps), explanation=side.path_explanation,
            confidence="medium", evidenceIds=_ids(evidence, 3, 3),
        )],
    )


def build_forecast(slug: str, pack: KnowledgePack, persona: str, evidence: list[Evidence],
                   generated_at: str, cutoff: str) -> WhatHappensNext:
    side = pack.persona(persona)
    return WhatHappensNext(
        generatedAt=generated_at, evidenceCutoff=cutoff,
        model="worldtune-knowledge-composer", promptVersion="world-shift-v3-knowledge",
        framing=side.scenario_framing,
        scenarios=[Scenario(
            id=f"{slug}:{persona}:scenario:{spec.label}", label=spec.label, title=spec.title,
            summary=spec.summary, horizon=spec.horizon, confidence=spec.confidence,
            triggers=list(spec.triggers), indicators=list(spec.indicators),
            invalidators=list(spec.invalidators), implications=list(spec.implications),
            evidenceIds=_ids(evidence, index * 6, 3), evidenceClass="inferred",
        ) for index, spec in enumerate(side.scenarios)],
        resolutionStatus="open",
    )


def compose_parts(slug: str, topic: str, category: str, persona: str, status: str,
                  peers: list[tuple[str, str]], observed_at: str, generated_at: str
                  ) -> tuple[Overview, Impact, list[DomainGroup], Relationships, WhatHappensNext, list[Evidence]]:
    """Build every persona-aware part of the contract for one shift."""
    artifact = artifact_for(slug)
    pack = knowledge_for(slug, topic, category)
    evidence = build_evidence(slug, artifact, observed_at)
    hero = _hero_evidence(slug, pack, observed_at)
    if hero is not None:
        evidence = evidence + [hero]
    return (
        build_overview(slug, pack, artifact, evidence, status),
        build_impact(slug, pack, persona, evidence),
        build_domain_groups(slug, pack, persona, evidence, artifact),
        build_relationships(slug, pack, persona, evidence, peers, observed_at, generated_at),
        build_forecast(slug, pack, persona, evidence, generated_at, observed_at),
        evidence,
    )
