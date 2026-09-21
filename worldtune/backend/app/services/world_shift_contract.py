"""Compose the immutable GDELT artifact into the frontend World Shift contract.

V1 deliberately stays GDELT-only. The composer labels persona and relationship text as
inferred/associated and never presents article attention as a market, hiring, or price result.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import select

from app.db import session_scope
from app.models import WorldShiftSnapshotORM
from app.schemas.world_shift import (
    CrossShiftLink,
    Evidence,
    EvidenceResponse,
    Impact,
    ImpactItem,
    IntelligencePoint,
    Overview,
    PersonalPath,
    PersonaContent,
    RelationshipEdge,
    RelationshipNode,
    Relationships,
    RelationshipsResponse,
    Scenario,
    SnapshotMeta,
    WorldShiftListItem,
    WorldShiftListResponse,
    WorldShiftSnapshot,
    ShiftOverview,
    WhatHappensNext,
    DomainEntity,
    DomainGroup,
)

ROOT = Path(__file__).resolve().parents[4]
DEFAULT_PATH = ROOT / "data/processed/worldtune/world_shifts/gold_world_shifts.parquet"


class WorldShiftDataUnavailable(RuntimeError):
    pass


class WorldShiftSnapshotMismatch(RuntimeError):
    pass


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _direction(value: str) -> str:
    return {"up": "up", "down": "down", "flat": "neutral"}.get(value, "uncertain")


def _status(value: str, direction: str) -> str:
    return {
        "SURGING": "surging",
        "RISING": "rising",
        "COOLING": "declining",
        "FALLING": "declining",
        "STABLE": "stable",
    }.get(value, "changing" if direction != "flat" else "watching")


def _magnitude(score: float) -> str:
    if score >= 0.8:
        return "critical"
    if score >= 0.6:
        return "high"
    if score >= 0.35:
        return "medium"
    return "low"


def _json_list(value: object) -> list:
    try:
        parsed = json.loads(value or "[]")
        return parsed if isinstance(parsed, list) else []
    except (TypeError, ValueError):
        return []


def _safe_entities(values: list, limit: int = 5) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text or text.isdigit() or len(text) < 2:
            continue
        if text not in result:
            result.append(text)
    return result[:limit]


def _editorial_context(topic: str, category: str, direction: str) -> tuple[str, str, str, list[str]]:
    """Turn a topic signal into readable context without inventing a specific event."""
    name = topic.strip()
    key = name.lower()
    contexts = {
        "armed conflict": (
            f"{name} is drawing sustained attention because security decisions can move through borders, energy, trade, supply chains, and civilian risk.",
            "The important question is whether attention reflects a contained episode or a wider change in security and economic conditions.",
            f"Reporting around {name} is {direction}; the next meaningful change would be independent confirmation of escalation, de-escalation, or spillover.",
            ["military and diplomatic actions", "energy and trade disruption", "humanitarian and infrastructure effects"],
        ),
        "inflation": (
            f"{name} matters because changes in prices and interest rates alter household purchasing power, business investment, and the cost of capital.",
            "The useful distinction is between a temporary price shock and a persistent change in inflation expectations or policy.",
            f"The {name} signal is {direction}; watch policy language, energy and food prices, wages, and credit conditions for confirmation.",
            ["central-bank guidance", "energy, food, and freight prices", "wages and credit conditions"],
        ),
        "ai infrastructure": (
            f"{name} is about the physical and operational layer behind AI: compute, data-centres, power, chips, cloud capacity, and the organisations deploying them.",
            "Its significance comes from whether new demand is becoming durable capacity or remaining concentrated in a small set of projects and suppliers.",
            f"Attention around {name} is {direction}; capacity announcements, power constraints, chip availability, and real deployments are the confirming signals.",
            ["compute and accelerator availability", "data-centre power and capacity", "production deployments"],
        ),
        "semiconductor": (
            f"{name} sits upstream of electronics, vehicles, cloud services, and AI systems, so supply decisions can ripple through many industries.",
            "The key issue is whether supply, export controls, or demand is changing the practical availability of critical components.",
            f"The {name} signal is {direction}; inventories, factory output, export rules, and lead times would confirm a broader shift.",
            ["factory output and inventories", "export controls", "lead times and end-market demand"],
        ),
        "cyber": (
            f"{name} matters because attacks and defensive responses can interrupt public services, businesses, identity systems, and critical infrastructure.",
            "A headline becomes consequential when there is evidence of affected systems, remediation costs, or a change in security practice—not simply more coverage.",
            f"Coverage of {name} is {direction}; disclosed impact, response actions, and repeat incidents are the signals to follow.",
            ["affected systems and services", "response and remediation", "repeat incidents and controls"],
        ),
    }
    for marker, value in contexts.items():
        if marker in key:
            return value
    return (
        f"{name} is receiving {direction} attention across the {category} domain, but the real-world significance depends on what decisions, institutions, or systems change next.",
        "Read the signal as an invitation to connect the reporting to mechanisms and affected people—not as proof that an outcome has already occurred.",
        f"The current {name} signal is {direction}; follow official actions, measured effects, and independent reporting for confirmation.",
        ["official decisions", "measured effects", "independent corroboration"],
    )


def _path() -> Path:
    return Path(os.environ.get("WORLD_TUNE_SHIFTS_PATH", str(DEFAULT_PATH)))


@lru_cache(maxsize=4)
def _load(path_text: str, mtime_ns: int, size: int) -> tuple[dict[str, Any], ...]:
    del mtime_ns, size
    path = Path(path_text)
    if not path.exists():
        raise WorldShiftDataUnavailable(f"World Shift artifact not found: {path}")
    suffix = path.suffix.lower()
    if suffix == ".csv":
        frame = pd.read_csv(path)
    elif suffix == ".json":
        frame = pd.DataFrame(json.loads(path.read_text()))
    else:
        frame = pd.read_parquet(path)
    rank_column = "priority_score" if "priority_score" in frame else "signal_strength"
    frame = frame.sort_values(["date", rank_column], ascending=[False, False])
    return tuple(frame.to_dict("records"))


def _rows() -> tuple[dict[str, Any], ...]:
    path = _path()
    try:
        stat = path.stat()
    except FileNotFoundError as exc:
        raise WorldShiftDataUnavailable(str(path)) from exc
    return _load(str(path), stat.st_mtime_ns, stat.st_size)


@lru_cache(maxsize=4)
def _meta(path_text: str, mtime_ns: int, size: int, latest_date: str) -> SnapshotMeta:
    path = Path(path_text)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    generated = datetime.fromisoformat(latest_date).replace(tzinfo=timezone.utc) + timedelta(hours=23, minutes=59, seconds=59)
    valid_until = generated + timedelta(days=1)
    return SnapshotMeta(
        snapshotId=f"{latest_date}-{digest}",
        generatedAt=generated.isoformat().replace("+00:00", "Z"),
        validUntil=valid_until.isoformat().replace("+00:00", "Z"),
    )


def _snapshot_meta(rows: tuple[dict[str, Any], ...]) -> SnapshotMeta:
    path = _path()
    try:
        stat = path.stat()
    except FileNotFoundError as exc:
        raise WorldShiftDataUnavailable(str(path)) from exc
    latest = str(rows[0]["date"])[:10]
    return _meta(str(path), stat.st_mtime_ns, stat.st_size, latest)


def _check_snapshot(meta: SnapshotMeta, snapshot_id: str | None) -> None:
    if snapshot_id and snapshot_id != meta.snapshot_id:
        raise WorldShiftSnapshotMismatch(
            f"Requested snapshot {snapshot_id!r} is not the current immutable snapshot"
        )


def _latest_rows(rows: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
    if not rows:
        return []
    latest = str(rows[0]["date"])[:10]
    return [row for row in rows if str(row["date"])[:10] == latest]


def _active_matches_artifact(active: list[WorldShiftSnapshotORM], rows: tuple[dict[str, Any], ...]) -> bool:
    """Accept persisted AI content only when it represents the current artifact.

    Refresh snapshots are intentionally persisted, but the deterministic artifact can be
    rebuilt independently.  Without this guard an older ACTIVE snapshot can continue to
    expose removed or below-threshold shifts after the artifact changes.
    """
    latest = sorted(_latest_rows(rows),
                    key=lambda row: float(row.get("priority_score", row.get("signal_strength", 0))),
                    reverse=True)
    expected = {_slug(str(row["topic"])) for row in latest[:len(active)]}
    actual = {str(row.shift_id) for row in active}
    return bool(expected) and actual == expected


def _list_item(row: dict[str, Any], rank: int) -> WorldShiftListItem:
    direction = str(row.get("direction", "uncertain"))
    return WorldShiftListItem(
        id=_slug(str(row["topic"])),
        title=str(row["topic"]),
        rank=rank,
        status=_status(str(row.get("direction_label", "")), direction),
        direction=_direction(direction),
    )


def _persona_mechanism(topic: str, category: str, persona: str) -> tuple[str, str]:
    if persona == "tech":
        return (
            f"{topic} can change technology priorities, compliance work, delivery risk, or demand for specialised skills.",
            "The professional effect depends on whether organisations translate the development into budgets, projects, and hiring.",
        )
    return (
        f"{topic} can transmit through policy, input costs, risk appetite, currencies, or sector expectations.",
        "The financial effect depends on measured market and company data that is not established by news attention alone.",
    )


def _evidence(row: dict[str, Any], slug: str) -> list[Evidence]:
    records = _json_list(row.get("representative_evidence"))
    date = str(row["date"])[:10] + "T00:00:00Z"
    result: list[Evidence] = []
    for index, record in enumerate(records):
        url = str(record.get("url", "")).strip()
        if not url.startswith(("http://", "https://")):
            continue
        evidence_id = f"{slug}:e{index + 1}"
        domain = str(record.get("domain") or "GDELT").strip()
        title = str(record.get("title") or "").strip()
        image_url = None
        snippet = None
        # Request paths are cache-only. Publisher enrichment belongs to the
        # background refresh job and is persisted in the active snapshot.
        image_url = str(record.get("imageUrl") or record.get("image_url") or "").strip() or None
        snippet = str(record.get("summary") or record.get("snippet") or "").strip() or None
        title = title or f"Reporting related to {str(row.get('topic') or slug)}"
        result.append(Evidence(
            id=evidence_id,
            type="news",
            source=domain,
            title=title,
            summary=snippet or f"A source record related to {str(row.get('topic') or slug)}. Open the original report for the publisher's full context.",
            publishedAt=date,
            url=url,
            imageUrl=image_url,
            entities=_safe_entities(_json_list(row.get("organizations")) + _json_list(row.get("locations"))),
            tags=["observed", "gdelt", str(row["category"])],
            relationshipRole="supports GDELT attention signal",
            confidence="low",
            supports=[f"{slug}:impact", f"{slug}:node"],
        ))
    return result


def _compose(row: dict[str, Any], rows: list[dict[str, Any]], persona: str, meta: SnapshotMeta) -> WorldShiftSnapshot:
    slug = _slug(str(row["topic"]))
    direction_raw = str(row.get("direction", "uncertain"))
    direction = _direction(direction_raw)
    priority = float(row.get("priority_score", row.get("signal_strength", 0.0)))
    signal_score = max(0.0, min(100.0, round(priority * 100, 2)))
    status = _status(str(row.get("direction_label", "")), direction_raw)
    evidence = _evidence(row, slug)
    evidence_ids = [item.id for item in evidence]
    magnitude = _magnitude(priority)
    category = str(row.get("category", "world"))
    topic = str(row["topic"])
    article_count = int(row.get("evidence_article_count", 0))
    domains = int(row.get("evidence_unique_domains", 0))
    related_candidates = []
    current_entities = set(_safe_entities(_json_list(row.get("organizations"))))
    for peer in rows:
        if peer is row:
            continue
        shared = current_entities & set(_safe_entities(_json_list(peer.get("organizations"))))
        same_category = str(peer.get("category")) == category
        related_score = (2 if same_category else 0) + min(2, len(shared))
        item = _list_item(peer, 0)
        item.relationship_reason = (
            f"Shares {', '.join(sorted(shared)[:2])}" if shared else
            f"Shares the {category} domain" if same_category else
            "Candidate cross-domain transmission path"
        )
        item.relationship_confidence = "medium" if related_score >= 2 else "low"
        related_candidates.append((related_score, float(peer.get("priority_score", 0)), item))
    related = [item for _, _, item in sorted(related_candidates, key=lambda value: (value[0], value[1]), reverse=True)[:5]]
    for index, item in enumerate(related, start=1):
        item.rank = index
    observed_date = str(row["date"])[:10] + "T00:00:00Z"
    editorial_happening, editorial_why, editorial_take, editorial_themes = _editorial_context(topic, category, status)

    mechanism, second_order = _persona_mechanism(topic, category, persona)
    impact = Impact(
            summary=(f"{editorial_why} This interpretation is evidence-linked and conditional; it does not establish causality."),
        directImpacts=[ImpactItem(
            id=f"{slug}:impact", title="What could change in the world",
            summary=editorial_happening,
            direction=direction, magnitude=magnitude, evidenceIds=evidence_ids,
        )] if evidence_ids else [],
        impactChain=[ImpactItem(
            id=f"{slug}:chain", title="Transmission mechanism", summary=mechanism,
            direction="uncertain", magnitude="low", evidenceIds=evidence_ids,
            evidenceClass="inferred", mechanism=mechanism, horizon="30d", confidence="low",
            invalidators=["No corresponding change appears in official, market, jobs, or developer data"],
        )] if evidence_ids else [],
        secondOrderEffects=[ImpactItem(
            id=f"{slug}:second-order", title="Conditional second-order effect", summary=second_order,
            direction="uncertain", magnitude="low", evidenceIds=evidence_ids,
            evidenceClass="inferred", mechanism=second_order, horizon="90d", confidence="low",
            invalidators=["The proposed transmission mechanism does not materialise"],
        )] if evidence_ids else [], opportunities=[],
        risks=[ImpactItem(
            id=f"{slug}:risk", title="Evidence limitation",
            summary="GDELT-only coverage can reflect syndication, selection, or media attention rather than real-world change.",
            direction="uncertain", magnitude="medium", evidenceIds=evidence_ids,
        )] if evidence_ids else [],
        watchItems=[ImpactItem(
            id=f"{slug}:watch", title="What to verify next",
            summary="Look for independent market, jobs, developer, or official evidence in a future V2 source bundle.",
            direction="uncertain", magnitude="low", evidenceIds=evidence_ids,
        )] if evidence_ids else [],
    )
    entities = _safe_entities(_json_list(row.get("organizations")))
    domain_items = [DomainEntity(
        id=f"{slug}:entity:{_slug(name)}", name=name, type="gdelt_entity",
        direction=direction, magnitude="low",
        summary="Mentioned in GDELT coverage; this does not establish business, career, or investment impact.",
        evidenceIds=evidence_ids,
    ) for name in entities]
    cross_links = [CrossShiftLink(
            shiftId=item.id, title=item.title, relationship="candidate_relationship",
            explanation=item.relationship_reason or "Candidate relationship", confidence="low",
            evidenceIds=evidence_ids[:3], indicators=["shared evidence", "shared entities", "temporal order"],
        ) for item in related[:3]]
    topic_node = RelationshipNode(
            id=f"{slug}:node", label=topic, type="gdelt_topic", category="observed",
            summary="GDELT-derived topic node.", direction=direction, magnitude=magnitude,
            evidenceIds=evidence_ids,
        )
    relationships = Relationships(
        nodes=([topic_node] + [RelationshipNode(
            id=f"{link.shift_id}:node", label=link.title, type="world_shift", category="inferred",
            summary=link.explanation, direction="uncertain", magnitude="low", evidenceIds=link.evidence_ids,
        ) for link in cross_links]) if evidence_ids else [],
        edges=[RelationshipEdge(
            id=f"{slug}:edge:{link.shift_id}", source=topic_node.id, target=f"{link.shift_id}:node",
            relationship=link.relationship, category="cross_shift", explanation=link.explanation,
            confidence=link.confidence, evidenceIds=link.evidence_ids, evidenceClass=link.evidence_class,
            mechanism=link.explanation, temporalOrder="candidate transmission path",
            firstObservedAt=observed_date, lastUpdatedAt=meta.generated_at,
        ) for link in cross_links],
        story={
            "why": "The node is ranked from deterministic impact-gravity, persona-relevance, attention, and evidence metrics.",
            "direction": "Direction describes GDELT attention, not an asset or career forecast.",
            "personaImpact": f"This is a {persona} interpretation of GDELT evidence only.",
        },
        crossShiftLinks=cross_links,
        personalPaths=[PersonalPath(
            id=f"{slug}:path:{persona}", title=f"Path to {persona} relevance", persona=persona,
            steps=[topic, "bounded transmission mechanism", "persona exposure", "indicator to monitor"],
            explanation=mechanism, confidence="low", evidenceIds=evidence_ids[:3],
        )] if evidence_ids else [],
    )
    overview = Overview(
        whatHappened=editorial_happening,
        whyItMatters=editorial_why,
        quickTake=editorial_take,
        characteristics=["Contextual interpretation", "Evidence-linked", f"{status.title()} signal"],
        themes=editorial_themes + [topic],
        whatsHappening=[IntelligencePoint(
            text=editorial_happening, evidenceClass="inferred", evidenceIds=evidence_ids[:3]
        )],
        whyItMattersPoints=[IntelligencePoint(
            text=editorial_why, evidenceClass="inferred", evidenceIds=evidence_ids[:3]
        )],
        keyDevelopments=[IntelligencePoint(
            text=f"The current reporting signal is {status}; the strongest next evidence would be {editorial_themes[0]}.",
            evidenceClass="calculated", evidenceIds=evidence_ids[:3]
        )],
        drivers=[IntelligencePoint(
            text=f"The main drivers to follow are {', '.join(editorial_themes)}.",
            evidenceClass="inferred", evidenceIds=evidence_ids[:3]
        )],
        watchNext=[IntelligencePoint(
            text=editorial_take, evidenceClass="inferred", evidenceIds=evidence_ids[:3]
        )],
        contradictions=[IntelligencePoint(
            text="Coverage intensity can move before the underlying situation changes; look for independent confirmation before treating this as a real-world shift.",
            evidenceClass="inferred", evidenceIds=evidence_ids[:3]
        )],
    )
    scenarios = [Scenario(
        id=f"{slug}:scenario:{label}", label=label, title=title, summary=summary, horizon=horizon,
        confidence="low", triggers=["independent corroboration"],
        indicators=["official action", "measured affected-system data"],
        invalidators=["credible counter-evidence", "no observed transmission"],
        implications=[mechanism], evidenceIds=evidence_ids[:3], evidenceClass="inferred",
    ) for label, title, summary, horizon in [
        ("base", "Current direction persists", "The observed signal continues without a structural break.", "30d"),
        ("upside", "Adaptation limits disruption", "Policy or operational adaptation contains the adverse pathway.", "90d"),
        ("downside", "Pressure broadens", "New evidence indicates wider disruption or constraint.", "30d"),
    ]] if evidence_ids else []
    return WorldShiftSnapshot(
        **meta.model_dump(), persona=persona,
        shift=ShiftOverview(
            id=slug, title=topic, summary=str(row.get("summary", "")), status=status,
            direction=direction, signalStrength=signal_score, updatedAt=observed_date,
            overview=overview, relatedShifts=related,
        ),
        content=PersonaContent(impact=impact, domain={"groups": [DomainGroup(
            id=f"{slug}:domain", title=f"GDELT entities · {category}", entityType="gdelt_entity",
            items=domain_items,
        )] if domain_items else []}),
        relationships=relationships, evidence=evidence, schemaVersion="2.0",
        whatHappensNext=WhatHappensNext(
            generatedAt=meta.generated_at, evidenceCutoff=observed_date, model="deterministic-fallback",
            promptVersion="world-shift-v2-fallback",
            framing="Conditional scenarios, not deterministic predictions or investment advice.",
            scenarios=scenarios, resolutionStatus="open",
        ),
    )


def list_contract_shifts(limit: int = 20) -> WorldShiftListResponse:
    rows = _rows()
    with session_scope() as session:
        persisted = session.scalars(select(WorldShiftSnapshotORM).where(
            WorldShiftSnapshotORM.lifecycle == "ACTIVE",
            WorldShiftSnapshotORM.persona == "tech",
        ).order_by(WorldShiftSnapshotORM.rank)).all()
        if persisted and _active_matches_artifact(persisted, rows):
            snapshots = [WorldShiftSnapshot.model_validate(row.payload) for row in persisted]
            first = snapshots[0]
            return WorldShiftListResponse(
                snapshotId=first.snapshot_id, generatedAt=first.generated_at, validUntil=first.valid_until,
                entries=[WorldShiftListItem(id=item.shift.id, title=item.shift.title, rank=index,
                    status=item.shift.status, direction=item.shift.direction) for index, item in enumerate(snapshots, 1)],
            )
    meta = _snapshot_meta(rows)
    latest = sorted(_latest_rows(rows), key=lambda row: float(row.get("priority_score", row.get("signal_strength", 0))), reverse=True)[:limit]
    return WorldShiftListResponse(**meta.model_dump(), entries=[_list_item(row, index) for index, row in enumerate(latest, 1)])


def get_contract_shift(shift_id: str, persona: str, snapshot_id: str | None = None) -> WorldShiftSnapshot:
    rows = _rows()
    with session_scope() as session:
        active_rows = session.scalars(select(WorldShiftSnapshotORM).where(
            WorldShiftSnapshotORM.lifecycle == "ACTIVE",
            WorldShiftSnapshotORM.persona == persona,
        ).order_by(WorldShiftSnapshotORM.rank)).all()
        if active_rows and _active_matches_artifact(active_rows, rows):
            active = next((item for item in active_rows if item.shift_id == shift_id), None)
        else:
            active = None
        if active:
            if snapshot_id and snapshot_id != active.snapshot_id:
                raise WorldShiftSnapshotMismatch(
                    f"Requested snapshot {snapshot_id!r} is not the current immutable snapshot"
                )
            return WorldShiftSnapshot.model_validate(active.payload)
    meta = _snapshot_meta(rows)
    _check_snapshot(meta, snapshot_id)
    latest = _latest_rows(rows)
    row = next((item for item in latest if _slug(str(item["topic"])) == shift_id or str(item.get("shift_id")) == shift_id), None)
    if row is None:
        raise KeyError(shift_id)
    return _compose(row, latest, persona, meta)


def get_contract_relationships(shift_id: str, persona: str, snapshot_id: str | None = None) -> RelationshipsResponse:
    snapshot = get_contract_shift(shift_id, persona, snapshot_id)
    meta = SnapshotMeta(
        snapshotId=snapshot.snapshot_id,
        generatedAt=snapshot.generated_at,
        validUntil=snapshot.valid_until,
    )
    return RelationshipsResponse(**meta.model_dump(), relationships=snapshot.relationships)


def get_contract_evidence(
    shift_id: str, persona: str, snapshot_id: str | None = None,
    *, evidence_type: str | None = None, source: str | None = None,
    tag: str | None = None, confidence: str | None = None, limit: int = 100,
) -> EvidenceResponse:
    snapshot = get_contract_shift(shift_id, persona, snapshot_id)
    evidence = snapshot.evidence
    if evidence_type:
        evidence = [item for item in evidence if item.type == evidence_type]
    if source:
        evidence = [item for item in evidence if item.source.lower() == source.lower()]
    if tag:
        evidence = [item for item in evidence if tag in item.tags]
    if confidence:
        evidence = [item for item in evidence if item.confidence == confidence]
    return EvidenceResponse(
        snapshotId=snapshot.snapshot_id,
        generatedAt=snapshot.generated_at,
        validUntil=snapshot.valid_until,
        evidence=evidence[:limit],
    )
    PersonalPath,
    Scenario,
