"""Background refresh orchestration and atomic World Shift publication."""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from urllib.parse import urlparse

import httpx
from sqlalchemy import select, update

from app.config import settings
from app.db import session_scope
from app.models import (
    WorldShiftClaimORM, WorldShiftEntityORM, WorldShiftEventORM, WorldShiftEvidenceORM,
    WorldShiftRefreshRunORM, WorldShiftRelationshipORM, WorldShiftSnapshotORM,
)
from app.schemas.world_shift import (
    CrossShiftLink, DomainGroup, Evidence, Impact, Overview, PersonalPath, PersonaContent,
    RelationshipEdge, RelationshipNode, Relationships, Scenario, ShiftOverview, SnapshotMeta,
    WhatHappensNext, WorldShiftSnapshot,
)
from app.services.world_shift_ai import WorldShiftGenerationService, WorldShiftWebResearchService
from app.services.world_shift_contract import _compose, _latest_rows, _rows, _slug, _snapshot_meta
from app.services.world_shift_runtime import get_runtime_values
from app.providers.news.gdelt import GDELTNewsProvider

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="worldtune-refresh")
_launch_lock = threading.Lock()


def _live_gdelt_rows(base_rows: tuple[dict, ...]) -> tuple[dict, ...]:
    """Overlay recent GDELT articles in the background refresh worker only."""
    try:
        # GDELT rejects windows shorter than roughly 15 minutes; use a
        # 30-minute overlap so a five-minute scheduler never misses articles.
        since = datetime.now(timezone.utc) - timedelta(minutes=30)
        events = GDELTNewsProvider().fetch_news(since=since, limit=250)
    except Exception:
        logger.exception("live GDELT overlay failed; using cached artifact")
        return base_rows
    if not events:
        return base_rows
    now_date = max(event.published_at for event in events).date().isoformat()
    updated: list[dict] = []
    for original in base_rows:
        row = dict(original)
        # Keep the full topic set in the same refresh window; only matched
        # topics receive new evidence below.
        row["date"] = now_date
        topic = str(row.get("topic", "")).lower()
        tokens = [token for token in topic.replace("-", " ").split() if len(token) >= 4]
        matched = [event for event in events if any(token in event.title.lower() for token in tokens)]
        if matched:
            records = json.loads(row.get("representative_evidence") or "[]")
            seen = {str(item.get("url")) for item in records}
            for event in matched:
                if event.url and event.url not in seen:
                    records.append({"title": event.title, "url": event.url, "domain": event.domain})
                    seen.add(event.url)
            row["representative_evidence"] = json.dumps(records[-10:])
            row["evidence_article_count"] = int(row.get("evidence_article_count", 0)) + len(matched)
            row["evidence_unique_domains"] = max(
                int(row.get("evidence_unique_domains", 0)),
                len({event.domain for event in matched if event.domain}),
            )
        updated.append(row)
    return tuple(updated)


class _MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title: str | None = None
        self.image: str | None = None
        self.description: str | None = None
        self._in_title = False
        self._title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {k.lower(): (v or "") for k, v in attrs}
        if tag.lower() == "title":
            self._in_title = True
        if tag.lower() == "meta":
            key = (values.get("property") or values.get("name") or "").lower()
            content = values.get("content", "").strip()
            if key in {"og:title", "twitter:title"} and content:
                self.title = self.title or content
            elif key in {"og:image", "twitter:image", "twitter:image:src"} and content:
                self.image = self.image or content
            elif key in {"description", "og:description"} and content:
                self.description = self.description or content

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self._in_title = False
            if not self.title:
                value = " ".join(self._title_parts).strip()
                self.title = value or None

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._title_parts.append(data.strip())


def _publisher_metadata(url: str) -> tuple[str | None, str | None, str | None]:
    """Inspect only the exact publisher URL; failure is intentionally non-fatal."""
    try:
        with httpx.Client(timeout=1.5, follow_redirects=True, headers={"User-Agent": settings.http_user_agent}) as client:
            response = client.get(url, headers={"Range": "bytes=0-262143"})
            response.raise_for_status()
        parser = _MetadataParser()
        parser.feed(response.text[:262144])
        return parser.title, parser.image, parser.description
    except Exception:
        return None, None, None


def _publisher_family(domain: str) -> str:
    labels = domain.lower().removeprefix("www.").split(".")
    return ".".join(labels[-2:]) if len(labels) >= 2 else domain


def _source_class(domain: str) -> str:
    value = domain.lower()
    if value.endswith((".gov", ".gov.in", ".europa.eu")) or value in {
        "sec.gov", "cftc.gov", "rbi.org.in", "federalreserve.gov", "ecb.europa.eu",
    }:
        return "primary"
    if any(token in value for token in ("yahoo.", "aol.", "openpr.", "bignewsnetwork.")):
        return "aggregator"
    return "secondary"


def _artifact_evidence(row: dict, *, enrich: bool = True, enrich_limit: int = 10) -> list[dict]:
    try:
        records = json.loads(row.get("representative_evidence") or "[]")
    except (TypeError, ValueError):
        records = []
    published_at = str(row["date"])[:10] + "T00:00:00Z"
    result: list[dict] = []
    seen_urls: set[str] = set()
    selected: list[tuple[dict, str, str]] = []
    for record in records[:10]:
        url = str(record.get("url") or "").strip()
        if not url.startswith(("http://", "https://")) or url in seen_urls:
            continue
        seen_urls.add(url)
        supplied = str(record.get("title") or "").strip()
        if supplied.lower().startswith(("source report from ", "gdelt source report from ")):
            supplied = ""
        selected.append((record, url, supplied))
    metadata: dict[str, tuple[str | None, str | None, str | None]] = {}
    targets = [url for _, url, supplied in selected if enrich and not supplied][:enrich_limit]
    if targets:
        with ThreadPoolExecutor(max_workers=min(8, len(targets)), thread_name_prefix="publisher-meta") as pool:
            metadata = dict(zip(targets, pool.map(_publisher_metadata, targets)))
    for record, url, supplied in selected:
        title, image, snippet = metadata.get(url, (None, None, None))
        domain = str(record.get("domain") or urlparse(url).netloc).lower()
        evidence_id = "ev_" + hashlib.sha256(url.encode()).hexdigest()[:16]
        result.append({
            "evidenceId": evidence_id, "type": "news", "source": domain or "GDELT",
            "sourceDomain": domain, "originalHeadline": supplied or title, "publishedAt": published_at,
            "url": url, "imageUrl": image, "sourceSnippet": snippet, "aiSummary": None,
            "tags": ["observed", "gdelt", str(row.get("category", "world"))],
            "eventIds": [], "claimIds": [], "entityIds": [], "evidenceClass": "observed",
            "sourceClass": _source_class(domain), "retrievalStatus": "complete" if snippet else "metadata_only",
            "publisherFamily": _publisher_family(domain),
        })
    families = {item["publisherFamily"] for item in result if item.get("publisherFamily")}
    normalized_titles: dict[str, int] = {}
    for item in result:
        key = " ".join(str(item.get("originalHeadline") or "").lower().split())
        if key:
            normalized_titles[key] = normalized_titles.get(key, 0) + 1
    for item in result:
        key = " ".join(str(item.get("originalHeadline") or "").lower().split())
        item["independentPublisherCount"] = max(1, len(families))
        item["corroborationStatus"] = (
            "syndicated" if key and normalized_titles.get(key, 0) > 1 else
            "independently_corroborated" if len(families) >= 2 else "single_source"
        )
    return result


def _namespace_semantics(shift_id: str, semantic):
    prefix = _slug(shift_id) + ":"
    entity_map = {item.entity_id: prefix + item.entity_id for item in semantic.entities}
    claim_map = {item.claim_id: prefix + item.claim_id for item in semantic.claims}
    event_map = {item.event_id: prefix + item.event_id for item in semantic.events}
    relationship_map = {item.relationship_id: prefix + item.relationship_id for item in semantic.relationships}
    for item in semantic.entities:
        item.entity_id = entity_map[item.entity_id]
    for item in semantic.claims:
        item.claim_id = claim_map[item.claim_id]
        item.entity_ids = [entity_map[x] for x in item.entity_ids if x in entity_map]
    for item in semantic.events:
        item.event_id = event_map[item.event_id]
        item.entity_ids = [entity_map[x] for x in item.entity_ids if x in entity_map]
    for item in semantic.relationships:
        item.relationship_id = relationship_map[item.relationship_id]
        item.source_entity_id = entity_map[item.source_entity_id]
        item.target_entity_id = entity_map[item.target_entity_id]
        item.claim_ids = [claim_map[x] for x in item.claim_ids if x in claim_map]
    return semantic


def _persist_semantics(session, shift_id: str, run_id: str, evidence: list[dict], semantic) -> None:
    for item in evidence:
        existing = session.get(WorldShiftEvidenceORM, item["evidenceId"])
        values = dict(
            evidence_id=item["evidenceId"], url=item["url"], source=item["source"],
            source_domain=item["sourceDomain"], original_headline=item["originalHeadline"],
            published_at=datetime.fromisoformat(item["publishedAt"].replace("Z", "+00:00")),
            image_url=item["imageUrl"], source_snippet=item["sourceSnippet"], ai_summary=item["aiSummary"],
            tags=item["tags"], first_run_id=run_id, last_run_id=run_id,
        )
        if existing:
            existing.last_run_id = run_id
            existing.original_headline = existing.original_headline or values["original_headline"]
            existing.image_url = existing.image_url or values["image_url"]
            existing.source_snippet = existing.source_snippet or values["source_snippet"]
        else:
            session.add(WorldShiftEvidenceORM(**values))
    for item in semantic.events:
        session.merge(WorldShiftEventORM(event_id=item.event_id, shift_id=shift_id, title=item.title,
            summary=item.summary, evidence_class=item.evidence_class, evidence_ids=item.evidence_ids,
            entity_ids=item.entity_ids, generation_run_id=run_id))
    for item in semantic.claims:
        session.merge(WorldShiftClaimORM(claim_id=item.claim_id, shift_id=shift_id, text=item.text,
            evidence_class=item.evidence_class, evidence_ids=item.evidence_ids, entity_ids=item.entity_ids,
            generation_run_id=run_id))
    for item in semantic.entities:
        session.merge(WorldShiftEntityORM(entity_id=item.entity_id, shift_id=shift_id, name=item.name,
            normalized_name=item.normalized_name, entity_type=item.entity_type,
            evidence_ids=item.evidence_ids, generation_run_id=run_id))
    for item in semantic.relationships:
        session.merge(WorldShiftRelationshipORM(relationship_id=item.relationship_id, shift_id=shift_id,
            source_entity_id=item.source_entity_id, target_entity_id=item.target_entity_id,
            relationship_type=item.relationship_type, label=item.label, evidence_class=item.evidence_class,
            evidence_ids=item.evidence_ids, claim_ids=item.claim_ids, generation_run_id=run_id))


_CROSS_SHIFT_RULES = {
    "armed-conflict-and-military-escalation": [("sanctions-and-economic-warfare", "can trigger sanctions and trade restrictions"), ("inflation-and-rates", "can transmit through energy and supply costs")],
    "sanctions-and-economic-warfare": [("armed-conflict-and-military-escalation", "often responds to geopolitical escalation"), ("inflation-and-rates", "can alter energy, trade, and input costs")],
    "inflation-and-rates": [("armed-conflict-and-military-escalation", "can absorb conflict-driven energy pressure"), ("ai-infrastructure", "changes the cost of capital for AI investment"), ("semiconductors", "changes financing and inventory conditions")],
    "ai-infrastructure": [("semiconductors", "depends on compute and accelerator supply"), ("cloud-infrastructure", "depends on cloud capacity and deployment"), ("cybersecurity", "creates new security and governance requirements")],
    "semiconductors": [("ai-infrastructure", "supplies compute capacity"), ("sanctions-and-economic-warfare", "is exposed to trade and export controls")],
    "cybersecurity": [("ai-infrastructure", "constrains trustworthy AI deployment"), ("cloud-infrastructure", "affects cloud controls and operating risk")],
    "crypto-regulation": [("india-digital-policy", "intersects digital payments and financial regulation")],
    "india-digital-policy": [("crypto-regulation", "shares digital-finance policy boundaries"), ("cloud-infrastructure", "depends on digital public and cloud infrastructure")],
    "cloud-infrastructure": [("ai-infrastructure", "hosts AI systems and data workloads"), ("cybersecurity", "depends on resilient identity and security controls")],
}


def _cross_shift_links(shift_id: str, rows: list[dict], evidence_ids: list[str]) -> list[CrossShiftLink]:
    titles = {_slug(str(item["topic"])): str(item["topic"]) for item in rows}
    result = []
    for target, explanation in _CROSS_SHIFT_RULES.get(shift_id, []):
        if target in titles:
            result.append(CrossShiftLink(
                shiftId=target, title=titles[target], relationship="connected_through_mechanism",
                explanation=explanation, confidence="low", evidenceClass="inferred",
                evidenceIds=evidence_ids[:3], indicators=["new corroborating evidence", "shared entities or policy actions"],
            ))
    return result


def _personal_paths(shift_id: str, topic: str, persona: str, evidence_ids: list[str], persona_view) -> list[PersonalPath]:
    impact_titles = [item.title for item in (persona_view.direct_impacts + persona_view.impact_chain + persona_view.second_order_effects)][:2]
    if persona == "tech":
        steps = [topic, "technology and policy mechanism", impact_titles[0] if impact_titles else "skills and delivery demand", "career and consulting relevance"]
        title = "Path to technology and career relevance"
    else:
        steps = [topic, "economic transmission mechanism", impact_titles[0] if impact_titles else "asset and sector exposure", "personal finance relevance"]
        title = "Path to finance and investing relevance"
    return [PersonalPath(id=f"{shift_id}:path:{persona}", title=title, persona=persona, steps=steps,
        explanation="A bounded interpretation path; each step remains conditional until supported by outcome data.",
        confidence="low", evidenceIds=evidence_ids[:3])]


def _fallback_scenarios(shift_id: str, topic: str, evidence_ids: list[str]) -> list[Scenario]:
    templates = [
        ("base", "Current direction persists", "30d", "Further independent reporting confirms the present direction without a structural break."),
        ("upside", "Constructive resolution or adaptation", "90d", "Policy, operational, or market adaptation reduces the adverse transmission channels."),
        ("downside", "Pressure broadens", "30d", "New evidence shows wider disruption, escalation, or regulatory constraint."),
    ]
    return [Scenario(
        id=f"{shift_id}:scenario:{label}", label=label, title=title, summary=summary,
        horizon=horizon, confidence="low", triggers=["new independently corroborated development"],
        indicators=["official action", "cross-source confirmation", "change in affected-system metrics"],
        invalidators=["credible contradictory evidence", "the expected mechanism does not appear"],
        implications=[f"Reassess the {topic} impact pathway for the selected persona"],
        evidenceIds=evidence_ids[:3], evidenceClass="inferred",
    ) for label, title, horizon, summary in templates]


def _snapshot_payload(row: dict, rows: list[dict], persona: str, meta: SnapshotMeta, evidence_data: list[dict], semantic, common, persona_view) -> WorldShiftSnapshot:
    base = _compose(row, rows, persona, meta)
    evidence_links = {item["evidenceId"]: {"events": [], "claims": [], "entities": []} for item in evidence_data}
    for event in semantic.events:
        for evidence_id in event.evidence_ids:
            evidence_links[evidence_id]["events"].append(event.event_id)
    for claim in semantic.claims:
        for evidence_id in claim.evidence_ids:
            evidence_links[evidence_id]["claims"].append(claim.claim_id)
    for entity in semantic.entities:
        for evidence_id in entity.evidence_ids:
            evidence_links[evidence_id]["entities"].append(entity.entity_id)
    families = {_publisher_family(str(item.get("sourceDomain") or item.get("source") or "")) for item in evidence_data}
    evidence = [Evidence(
        id=item["evidenceId"], type=item["type"], source=item["source"],
        title=item["originalHeadline"] or "Headline unavailable", summary=item["aiSummary"] or item["sourceSnippet"],
        publishedAt=item["publishedAt"], url=item["url"], imageUrl=item["imageUrl"],
        entities=[], tags=item["tags"], confidence="medium", supports=(evidence_links[item["evidenceId"]]["claims"] + evidence_links[item["evidenceId"]]["events"]),
        sourceDomain=item["sourceDomain"], originalHeadline=item["originalHeadline"], sourceSnippet=item["sourceSnippet"],
        aiSummary=item["aiSummary"], eventIds=evidence_links[item["evidenceId"]]["events"],
        claimIds=evidence_links[item["evidenceId"]]["claims"], entityIds=evidence_links[item["evidenceId"]]["entities"],
        evidenceClass="observed", sourceClass=item.get("sourceClass") or _source_class(str(item.get("sourceDomain") or "")),
        retrievalStatus=item.get("retrievalStatus", "metadata_only"),
        publisherFamily=item.get("publisherFamily") or _publisher_family(str(item.get("sourceDomain") or "")),
        independentPublisherCount=item.get("independentPublisherCount", max(1, len(families))),
        corroborationStatus=item.get("corroborationStatus", "independently_corroborated" if len(families) >= 2 else "single_source"),
    ) for item in evidence_data]
    base.evidence = evidence
    base.shift.summary = common.summary
    base.shift.overview = Overview(
        whatHappened=" ".join(point.text for point in common.whats_happening),
        whyItMatters=" ".join(point.text for point in common.why_it_matters),
        quickTake=common.quick_take, characteristics=base.shift.overview.characteristics,
        themes=common.key_themes, whatsHappening=common.whats_happening,
        whyItMattersPoints=common.why_it_matters, keyDevelopments=common.key_developments,
        watchNext=common.watch_next, drivers=common.drivers, contradictions=common.contradictions,
    )
    base.content = PersonaContent(impact=Impact(
        summary=persona_view.summary, directImpacts=persona_view.direct_impacts,
        impactChain=persona_view.impact_chain, secondOrderEffects=persona_view.second_order_effects, opportunities=persona_view.opportunities,
        risks=persona_view.risks, watchItems=persona_view.watch_items,
    ), domain={"groups": persona_view.domain_groups})
    cross_links = _cross_shift_links(base.shift.id, rows, [item.id for item in evidence])
    entity_nodes = [RelationshipNode(id=e.entity_id, label=e.name, type=e.entity_type, category="observed",
            summary=f"Grounded entity: {e.name}", evidenceIds=e.evidence_ids) for e in semantic.entities]
    topic_node = RelationshipNode(id=f"{base.shift.id}:topic", label=base.shift.title, type="world_shift",
            category="observed", summary="The shift being explained.", evidenceIds=[item.id for item in evidence])
    cross_nodes = [RelationshipNode(id=f"{link.shift_id}:topic", label=link.title, type="world_shift",
            category="inferred", summary=link.explanation, evidenceIds=link.evidence_ids) for link in cross_links]
    cross_edges = [RelationshipEdge(id=f"{base.shift.id}:edge:{link.shift_id}", source=topic_node.id,
            target=f"{link.shift_id}:topic", relationship=link.relationship, category="cross_shift",
            explanation=link.explanation, confidence=link.confidence, evidenceIds=link.evidence_ids,
            evidenceClass=link.evidence_class, mechanism=link.explanation,
            temporalOrder="candidate transmission path", firstObservedAt=base.shift.updated_at,
            lastUpdatedAt=meta.generated_at) for link in cross_links]
    base.relationships = Relationships(
        nodes=[topic_node, *entity_nodes, *cross_nodes],
        edges=[RelationshipEdge(id=r.relationship_id, source=r.source_entity_id, target=r.target_entity_id,
            relationship=r.relationship_type, explanation=r.label, confidence="medium",
            evidenceIds=r.evidence_ids, claimIds=r.claim_ids, evidenceClass=r.evidence_class,
            mechanism=r.label, temporalOrder="source-stated or same-snapshot association",
            firstObservedAt=base.shift.updated_at, lastUpdatedAt=meta.generated_at) for r in semantic.relationships] + cross_edges,
        story=common.relationship_story,
        crossShiftLinks=cross_links,
        personalPaths=_personal_paths(base.shift.id, base.shift.title, persona, [item.id for item in evidence], persona_view),
    )
    base.schema_version = settings.world_shift_schema_version
    base.what_happens_next = WhatHappensNext(
        generatedAt=meta.generated_at, evidenceCutoff=base.shift.updated_at, model=settings.llm_model,
        promptVersion=settings.world_shift_prompt_version,
        framing="Conditional scenarios, not deterministic predictions or investment advice.",
        scenarios=common.scenarios or _fallback_scenarios(base.shift.id, base.shift.title, [item.id for item in evidence]),
        resolutionStatus="open",
    )
    return base


class RefreshService:
    def request_refresh(self) -> WorldShiftRefreshRunORM:
        with _launch_lock, session_scope() as session:
            active = session.scalars(select(WorldShiftRefreshRunORM).where(
                WorldShiftRefreshRunORM.status.in_(["queued", "running"])
            ).order_by(WorldShiftRefreshRunORM.created_at.desc())).first()
            if active:
                return active
            run_id = "run_" + uuid.uuid4().hex
            current = session.scalars(select(WorldShiftSnapshotORM.snapshot_id).where(
                WorldShiftSnapshotORM.lifecycle == "ACTIVE"
            )).first()
            if not current:
                try:
                    current = _snapshot_meta(_rows()).snapshot_id
                except Exception:
                    current = None
            run = WorldShiftRefreshRunORM(run_id=run_id, status="queued", stage="fetching_gdelt",
                completed=0, total=10, current_snapshot_id=current)
            session.add(run)
            session.flush()
            session.expunge(run)
        _executor.submit(self._run, run_id)
        return run

    def get(self, run_id: str) -> WorldShiftRefreshRunORM:
        with session_scope() as session:
            run = session.get(WorldShiftRefreshRunORM, run_id)
            if not run:
                raise KeyError(run_id)
            session.expunge(run)
            return run

    @staticmethod
    def _update(run_id: str, *, stage: str, completed: int | None = None, **values) -> None:
        with session_scope() as session:
            run = session.get(WorldShiftRefreshRunORM, run_id)
            if run:
                run.stage = stage
                run.status = values.pop("status", "running")
                if completed is not None:
                    run.completed = completed
                for key, value in values.items():
                    setattr(run, key, value)
                run.updated_at = datetime.now(timezone.utc)

    def _run(self, run_id: str) -> None:
        snapshot_id = "snap_" + uuid.uuid4().hex[:20]
        try:
            # Network ingestion happens in the worker; API reads remain cache-first.
            # Refresh from the bounded local artifact. Live GDELT overlay is
            # intentionally kept out of the publication critical path because
            # provider throttling/timeouts must not prevent a v2 snapshot.
            rows_tuple = _rows()
            rows = sorted(_latest_rows(rows_tuple),
                          key=lambda x: float(x.get("priority_score", x.get("signal_strength", 0))),
                          reverse=True)
            rows = rows[:settings.world_shift_refresh_max_shifts]
            if not rows:
                raise RuntimeError("No latest GDELT World Shifts are available")
            date = datetime.fromisoformat(str(rows[0]["date"])[:10]).replace(tzinfo=timezone.utc)
            _, web_research_enabled, web_results_per_shift = get_runtime_values()
            total = len(rows) * (5 if web_research_enabled else 4) + 4
            self._update(run_id, stage="normalizing", completed=1, total=total,
                window_start=date, window_end=date + timedelta(days=1),
                records_fetched=sum(int(r.get("evidence_article_count", 0)) for r in rows))
            generator = WorldShiftGenerationService()
            researcher = WorldShiftWebResearchService()
            meta = SnapshotMeta(snapshotId=snapshot_id, generatedAt=datetime.now(timezone.utc).isoformat(),
                                validUntil=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat())
            built: list[WorldShiftSnapshotORM] = []
            completed = 2
            with session_scope() as session:
                for rank, row in enumerate(rows, 1):
                    shift_id = _slug(str(row["topic"]))
                    self._update(run_id, stage="building_evidence", completed=completed)
                    # Publisher metadata is best-effort enrichment. Do not let an
                    # arbitrary publisher connection block publication of the v2
                    # snapshot; the supplied GDELT URL/headline remains valid
                    # evidence when metadata retrieval is unavailable.
                    evidence = _artifact_evidence(row, enrich=False)
                    if not evidence:
                        raise RuntimeError(f"No bounded evidence for {shift_id}")
                    metrics = {"articleCount": int(row.get("evidence_article_count", 0)),
                               "uniqueDomains": int(row.get("evidence_unique_domains", 0)),
                               "signalStrength": float(row.get("signal_strength", 0)),
                               "worldImpact": float(row.get("world_impact_score", 0)),
                               "personaImpact": float(row.get("persona_impact_score", 0)),
                               "impactGravity": float(row.get("impact_gravity_score", 0)),
                               "priorityScore": float(row.get("priority_score", row.get("signal_strength", 0))),
                               "direction": str(row.get("direction", "uncertain"))}
                    try:
                        if web_research_enabled:
                            self._update(run_id, stage="researching_web", completed=completed)
                            try:
                                researched = researcher.research(
                                    session, shift_id=shift_id, topic=str(row["topic"]),
                                    category=str(row.get("category", "world")), evidence=evidence,
                                    run_id=run_id, max_results=web_results_per_shift,
                                )
                                seen = {item["url"] for item in evidence}
                                evidence.extend(item for item in researched if item["url"] not in seen)
                                session.commit()
                            except Exception:
                                logger.exception("bounded web research failed for %s; continuing with GDELT evidence", shift_id)
                                session.rollback()
                            completed += 1
                        semantic = generator.extract(session, shift_id=shift_id, evidence=evidence, metrics=metrics, run_id=run_id)
                        semantic = _namespace_semantics(shift_id, semantic)
                        session.commit()  # release SQLite writer lock before status update
                        completed += 1; self._update(run_id, stage="extracting_semantics", completed=completed)
                        common = generator.synthesize(session, shift_id=shift_id, evidence=evidence, semantic=semantic, metrics=metrics, run_id=run_id)
                        _persist_semantics(session, shift_id, run_id, evidence, semantic)
                        session.commit()
                        completed += 1; self._update(run_id, stage="generating_overview", completed=completed)
                        for persona in ("finance", "tech"):
                            self._update(run_id, stage=f"generating_{persona}", completed=completed)
                            view = generator.persona(session, shift_id=shift_id, persona=persona, evidence=evidence,
                                                     semantic=semantic, common=common, run_id=run_id)
                            session.commit()
                            snapshot = _snapshot_payload(row, rows, persona, meta, evidence, semantic, common, view)
                            built.append(WorldShiftSnapshotORM(snapshot_id=snapshot_id, shift_id=shift_id,
                                persona=persona, lifecycle="BUILDING", rank=rank,
                                payload=snapshot.model_dump(by_alias=True), generation_run_id=run_id,
                                valid_until=datetime.now(timezone.utc) + timedelta(days=1)))
                            completed += 1
                    except Exception:
                        # A malformed/overlong model response must not discard the
                        # entire hourly publication. Keep this shift available from
                        # deterministic GDELT evidence and continue with the rest.
                        logger.exception("AI generation failed for %s; publishing deterministic fallback", shift_id)
                        session.rollback()
                        fallback = _compose(row, rows, "tech", meta)
                        for persona in ("finance", "tech"):
                            if any(item.shift_id == shift_id and item.persona == persona for item in built):
                                continue
                            fallback.persona = persona
                            built.append(WorldShiftSnapshotORM(snapshot_id=snapshot_id, shift_id=shift_id,
                                persona=persona, lifecycle="BUILDING", rank=rank,
                                payload=fallback.model_dump(by_alias=True), generation_run_id=run_id,
                                valid_until=datetime.now(timezone.utc) + timedelta(days=1)))
                        completed = max(completed, 2 + rank * 4)
                        self._update(run_id, stage="fallback_published", completed=completed)
                session.add_all(built)
            self._update(run_id, stage="validating", completed=completed,
                         ai_generations_attempted=generator.attempted, ai_generations_reused=generator.reused,
                         validation_failures=generator.validation_failures,
                         shifts_generated=len(rows), records_deduplicated=sum(
                             max(0, len(json.loads(r.get("representative_evidence") or "[]")[:10]) - len(_artifact_evidence(r, enrich=False)))
                             for r in rows
                         ))
            self._update(run_id, stage="publishing", completed=total - 1)
            promote_snapshot(snapshot_id)
            self._update(run_id, stage="complete", completed=total, status="completed", new_snapshot_id=snapshot_id)
        except Exception as exc:
            logger.exception("World Shift refresh %s failed", run_id)
            with session_scope() as session:
                session.execute(update(WorldShiftSnapshotORM).where(
                    WorldShiftSnapshotORM.snapshot_id == snapshot_id).values(lifecycle="FAILED"))
            self._update(run_id, stage="failed", status="failed", error=str(exc)[:1000])


refresh_service = RefreshService()


def promote_snapshot(snapshot_id: str) -> None:
    """Single-transaction lifecycle swap; no BUILDING row can leak as ACTIVE."""
    with session_scope() as session:
        building = session.scalar(select(WorldShiftSnapshotORM.id).where(
            WorldShiftSnapshotORM.snapshot_id == snapshot_id,
            WorldShiftSnapshotORM.lifecycle == "BUILDING",
        ).limit(1))
        if building is None:
            raise RuntimeError(f"No BUILDING snapshot rows for {snapshot_id}")
        session.execute(update(WorldShiftSnapshotORM).where(
            WorldShiftSnapshotORM.lifecycle == "ACTIVE").values(lifecycle="HISTORICAL"))
        session.execute(update(WorldShiftSnapshotORM).where(
            WorldShiftSnapshotORM.snapshot_id == snapshot_id,
            WorldShiftSnapshotORM.lifecycle == "BUILDING").values(lifecycle="ACTIVE"))


def refresh_status_dict(run: WorldShiftRefreshRunORM) -> dict:
    return {"runId": run.run_id, "status": run.status, "stage": run.stage,
            "progress": {"completed": run.completed, "total": run.total},
            "currentSnapshotId": run.current_snapshot_id, "newSnapshotId": run.new_snapshot_id,
            "error": run.error}
