"""Compose the immutable GDELT artifact into the frontend World Shift contract.

V1 deliberately stays GDELT-only. The composer labels persona and relationship text as
inferred/associated and never presents article attention as a market, hiring, or price result.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from urllib.parse import urlparse
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
    ExposureItem,
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
    ContextBrief,
    TimelineEvent,
    ActorBrief,
    FactFigure,
)
from app.services.world_shift_editorial import CONFLICT_ID, editorial_bundle
from app.services.world_shift_intelligence import compose_parts, has_intelligence

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


def _is_trending(row: dict[str, Any]) -> bool:
    value = row.get("is_trending")
    return bool(value) and value is not None and not (isinstance(value, float) and value != value)  # nan-safe


def _list_item(row: dict[str, Any], rank: int) -> WorldShiftListItem:
    direction = str(row.get("direction", "uncertain"))
    return WorldShiftListItem(
        id=_slug(str(row["topic"])),
        title=str(row["topic"]),
        rank=rank,
        status=_status(str(row.get("direction_label", "")), direction),
        direction=_direction(direction),
        isTrending=_is_trending(row),
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
        if not title:
            path = urlparse(url).path.rstrip("/").split("/")[-1]
            title = re.sub(r"[-_]+", " ", path).strip().capitalize() or f"Latest reporting on {str(row.get('topic') or slug)}"
        result.append(Evidence(
            id=evidence_id,
            type="news",
            source=domain,
            title=title,
            summary=snippet or f"Open the original report from {domain} for the publisher's full context.",
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


def _editorial_evidence(slug: str) -> list[Evidence]:
    bundle = editorial_bundle(slug)
    if not bundle:
        return []
    entities = ["United States", "Iran", "Israel", "Houthis", "Saudi Arabia", "Yemen"]
    return [Evidence(
        id=item["id"], type=item.get("type", "news"), source=item["source"], title=item["title"],
        summary=item["summary"], publishedAt=item["publishedAt"], url=item["url"],
        imageUrl=item.get("imageUrl"), entities=item.get("entities", entities),
        tags=["editorial-brief", "conflict", "Middle East", "company-context" if item.get("type") == "company disclosure" else "source"],
        relationshipRole="supports the consolidated chronology and actor briefing",
        confidence="medium", supports=[f"{slug}:story", f"{slug}:timeline"],
        sourceDomain=item["url"].split("/")[2], originalHeadline=item["title"],
        sourceSnippet=item["summary"], evidenceClass="observed",
        sourceClass=item.get("sourceClass", "secondary"), retrievalStatus="complete",
        publisherFamily=item["source"], independentPublisherCount=5,
        corroborationStatus="independently_corroborated",
    ) for item in bundle["evidence"]]


def _conflict_persona_content(persona: str, evidence_ids: list[str]) -> tuple[Impact, list[DomainGroup]]:
    def item(suffix: str, title: str, summary: str, mechanism: str, horizon: str = "30d") -> ImpactItem:
        return ImpactItem(
            id=f"armed-conflict-and-military-escalation:{suffix}", title=title, summary=summary,
            direction="uncertain", magnitude="high", evidenceIds=evidence_ids,
            evidenceClass="inferred", mechanism=mechanism, horizon=horizon, confidence="medium",
            invalidators=["Verified de-escalation restores safe passage and removes the stated transmission mechanism"],
        )

    chains = [
        item("chain-energy", "Attacks or threats near shipping lanes → energy risk premium",
             "Pressure around Hormuz or Bab el-Mandeb can interrupt cargoes or make shipowners pay more for war-risk insurance. That can lift oil, fuel and freight costs even before physical supply falls.",
             "security threat → insurance and rerouting costs → tighter effective supply → higher energy and freight prices", "7d"),
        item("chain-inflation", "Higher oil and freight costs → inflation and interest-rate pressure",
             "Countries that import energy can face more expensive transport, electricity and goods. If the shock persists, central banks may have less room to cut rates, affecting bonds, currencies and rate-sensitive equities.",
             "oil/freight shock → import costs and inflation → policy-rate expectations → asset repricing", "30d"),
        item("chain-defense", "Interceptor use → defence replenishment demand",
             "Sustained missile and drone attacks consume expensive interceptors. Replenishment can support defence orders but also strains inventories, government budgets and production capacity.",
             "attacks → interceptor depletion → procurement and production demand → fiscal and supply-chain effects", "90d"),
    ]
    direct = [
        item("direct-shipping", "Shipping and insurance", "The most immediate exposure is passage through Hormuz and Bab el-Mandeb: delays, war-risk premiums and rerouting can raise delivered costs.", "military risk near chokepoints → shipping decisions", "7d"),
        item("direct-energy", "Oil and fuel", "Iran and Saudi Arabia sit close to critical production and export infrastructure. Escalation can add a geopolitical premium; de-escalation can remove it quickly.", "threat to production/export routes → price volatility", "7d"),
    ]
    impact = Impact(
        summary="The market risk is not simply that conflict is in the news. It is whether military action changes the safe movement of energy and trade, consumes scarce defence capacity, or alters inflation and policy expectations.",
        directImpacts=direct, impactChain=chains, secondOrderEffects=[
            item("second-growth", "Import-dependent economies and companies", "Energy-importing countries and fuel-intensive businesses can face weaker margins, larger import bills and currency pressure if the shock persists.", "higher landed energy cost → margins/current account → growth and currency pressure", "90d")
        ], opportunities=[], risks=[
            item("risk-escalation", "Misreading attributed claims", "Several fast-moving events are claims by combatants or governments. Treat direction and responsibility as provisional until independently corroborated.", "single-party claim → premature market conclusion", "7d")
        ], watchItems=[
            item("watch-routes", "What would confirm the market effect", "Watch verified vessel transit, insurance premiums, oil export volumes, port closures, Brent prices and official de-escalation agreements—not headline volume alone.", "observable route and price data confirms or rejects the pathway", "7d")
        ],
    )
    conflict_sources = [
        "armed-conflict-and-military-escalation:brief:cfr",
        "armed-conflict-and-military-escalation:brief:ap-saudi",
    ]
    def exposure(suffix: str, company: str, ticker: str | None, direction: str, ring: str,
                 mechanism: str, reasoning: list[str], countries: list[str], horizons: list[str],
                 company_source: str, verification: str, opportunity_type: str) -> ExposureItem:
        return ExposureItem(
            id=f"armed-conflict-and-military-escalation:exposure:{suffix}",
            entityName=company, ticker=ticker, direction=direction, ring=ring,
            mechanism=mechanism, reasoning=reasoning, confidence="medium",
            derivedFrom=conflict_sources, verificationHint=verification,
            evidenceIds=conflict_sources + [company_source], evidenceClass="reasoned",
            horizons=horizons, countries=countries, opportunityType=opportunity_type,
        )
    if persona == "finance":
        impact.exposure_map = [
            exposure("lmt", "Lockheed Martin", "NYSE: LMT", "positive", "direct",
                "Possible favourable revenue exposure if interceptor replenishment and production expansion convert into funded deliveries; the existing multiyear contracts matter more than a single headline.",
                ["Missile and drone attacks consume air-defence interceptors.", "Governments may replenish depleted stocks.", "Lockheed produces PAC-3 and THAAD interceptors and is expanding capacity.", "Revenue timing still depends on appropriations, contract ceilings and delivery schedules."],
                ["United States", "Gulf allies", "Europe"], ["near_term", "long_term"],
                "armed-conflict-and-military-escalation:company:lockheed",
                "Check funded backlog, PAC-3/THAAD delivery volumes, margins and whether new awards are incremental to contracts already priced in.", "air and missile defence"),
            exposure("rtx", "RTX", "NYSE: RTX", "positive", "direct",
                "Possible favourable demand exposure through Patriot radar, command-and-control and interceptor replenishment, conditional on actual orders and production capacity.",
                ["Regional missile and drone activity raises demand for detection and interception.", "RTX supplies major Patriot system components.", "Operational demand does not automatically become new revenue or a higher share price."],
                ["United States", "Saudi Arabia", "Gulf allies", "Europe"], ["near_term", "long_term"],
                "armed-conflict-and-military-escalation:company:rtx",
                "Check disclosed Patriot awards, backlog conversion, supplier constraints and programme margins.", "integrated air defence"),
            exposure("bel", "Bharat Electronics", "NSE: BEL", "positive", "supply_chain",
                "India-based indirect exposure through radars, electronic warfare, communications and anti-drone systems; benefit requires Indian or export procurement, not merely a foreign conflict.",
                ["The conflict demonstrates demand for sensor fusion, radar and electronic warfare.", "BEL discloses products and R&D in these areas.", "A commercial effect requires a separate Indian or export order."],
                ["India"], ["long_term"], "armed-conflict-and-military-escalation:tech:bdl",
                "Check Ministry of Defence awards, BEL order intake, execution schedule, localisation and receivable days.", "Indian defence electronics"),
            exposure("bdl", "Bharat Dynamics", "NSE: BDL", "positive", "supply_chain",
                "Potential long-term sensitivity to Indian missile replenishment and air-defence procurement, but no order should be inferred from this conflict alone.",
                ["Missile-intensive conflict can influence preparedness reviews.", "BDL manufactures missile systems for India's armed forces.", "Only a disclosed procurement decision turns the theme into company revenue."],
                ["India"], ["long_term"], "armed-conflict-and-military-escalation:tech:bel",
                "Verify BDL order announcements, programme mix, delivery milestones and government budget allocation.", "Indian missile systems"),
            exposure("ongc", "ONGC", "NSE: ONGC", "mixed", "second_order",
                "Higher crude prices may improve upstream realisations in the near term, while government intervention, taxes and demand destruction can offset the benefit.",
                ["Shipping risk can add an oil-price premium.", "Upstream producers can receive higher realisations.", "India's policy and fiscal response can alter how much reaches shareholders."],
                ["India"], ["near_term"], "armed-conflict-and-military-escalation:india:oil",
                "Track realised crude price, windfall taxes or subsidy-sharing, production volumes and Brent rather than the headline alone.", "energy-price sensitivity"),
            exposure("ioc", "Indian Oil", "NSE: IOC", "negative", "second_order",
                "Higher imported crude and working-capital needs can pressure refining and marketing economics when retail prices do not adjust at the same speed.",
                ["India imports most of the crude it consumes.", "A conflict premium raises feedstock and financing costs.", "Refining margins and policy pass-through determine the net company effect."],
                ["India"], ["near_term"], "armed-conflict-and-military-escalation:india:oil",
                "Track gross refining margin, inventory gains or losses, marketing margin, retail-price policy and working capital.", "downstream oil and marketing"),
            exposure("indigo", "InterGlobe Aviation / IndiGo", "NSE: INDIGO", "negative", "direct",
                "Direct near-term sensitivity to aviation fuel, insurance, airspace closures and longer routings; fares and capacity adjustments can partly offset those costs.",
                ["The conflict can restrict Middle East airspace and raise fuel and insurance costs.", "IndiGo has identified those same channels in its operating updates.", "The financial outcome depends on duration, hedging, fares and network changes."],
                ["India", "Saudi Arabia", "Oman", "Middle East routes"], ["near_term"],
                "armed-conflict-and-military-escalation:india:indigo",
                "Check cancelled or rerouted flights, ATF prices, fuel CASK, insurance expense, load factors and fare recovery.", "aviation and travel"),
        ]
        groups = [DomainGroup(id="conflict:finance", title="Your finance & investing lens", entityType="exposure", items=[
            DomainEntity(id="conflict:finance:energy", name="Energy and refiners", type="sector", direction="uncertain", magnitude="high", summary="Potential upside from a risk premium can coexist with demand destruction and rapid reversal if shipping normalises.", evidenceIds=evidence_ids),
            DomainEntity(id="conflict:finance:transport", name="Airlines, shipping and logistics", type="sector", direction="down", magnitude="high", summary="Fuel, insurance, route length and operational disruption are the direct cost channels.", evidenceIds=evidence_ids),
            DomainEntity(id="conflict:finance:rates", name="Bonds, currencies and rate-sensitive equities", type="asset channel", direction="uncertain", magnitude="medium", summary="A persistent energy shock can raise inflation expectations and delay rate cuts; a short shock may fade without changing policy.", evidenceIds=evidence_ids),
            DomainEntity(id="conflict:finance:defense", name="Defence supply chain", type="sector", direction="up", magnitude="medium", summary="Interceptor depletion can support replenishment demand, subject to budgets, capacity and contract timing.", evidenceIds=evidence_ids),
        ])]
    else:
        impact.summary = "The technology opportunity is not the conflict itself. It is the accelerated need for cheaper interception, resilient navigation and communications, sensor fusion, autonomous surveillance, cyber resilience and rapid decision support. Company relevance still requires actual procurement or deployment evidence."
        impact.exposure_map = [
            exposure("tech-lockheed", "Lockheed Martin", "NYSE: LMT", "positive", "direct",
                "Near-term engineering opportunity in scaling PAC-3/THAAD manufacturing; longer-term opportunity in lower-cost interceptors, digital production and networked sensor-to-shooter integration.",
                ["Interceptor demand exposes inventory and cost constraints.", "Scaling needs robotics, digital twins, supplier automation and test systems.", "Future systems also need cheaper cost per interception."],
                ["United States", "Allied countries"], ["near_term", "long_term"],
                "armed-conflict-and-military-escalation:company:lockheed",
                "Look for production-rate milestones, lower-cost interceptor programmes, systems-integration roles and engineering hiring tied to funded awards.", "advanced manufacturing and missile defence"),
            exposure("tech-rtx", "RTX", "NYSE: RTX", "positive", "direct",
                "Opportunity in radar, command-and-control, multi-sensor tracking and lower-cost defeat of drones and missiles within integrated air-defence networks.",
                ["Mixed drone and missile threats require detection, classification and weapon assignment.", "Patriot combines radar, command-and-control and interceptors.", "The advancement path is better sensor fusion and cheaper layered defence."],
                ["United States", "Saudi Arabia", "Gulf allies"], ["near_term", "long_term"],
                "armed-conflict-and-military-escalation:company:rtx",
                "Track funded radar upgrades, software releases, interceptor mix and operational test results.", "radar and command systems"),
            exposure("tech-palantir", "Palantir", "NYSE: PLTR", "positive", "second_order",
                "Possible long-term opportunity for secure AI decision support, logistics planning and intelligence fusion, but this conflict does not establish a new Palantir contract.",
                ["Distributed operations create large, fast-moving data flows.", "Operators need auditable decisions on private and tactical networks.", "Palantir markets AIP and Gotham for this class of problem."],
                ["United States", "Allied countries"], ["long_term"],
                "armed-conflict-and-military-escalation:tech:palantir",
                "Verify programme awards, government revenue concentration, deployment scope and whether pilots become production contracts.", "defence AI and decision support"),
            exposure("tech-blacksky", "BlackSky", "NYSE: BKSY", "positive", "second_order",
                "Possible demand for high-frequency satellite imagery and AI geospatial analytics to monitor ports, airfields, shipping and damage, subject to tasking contracts.",
                ["A multi-front conflict needs repeated observation across wide areas.", "Commercial satellites can shorten collection cycles.", "Commercial opportunity exists only when agencies or enterprises purchase capacity and analytics."],
                ["United States", "Middle East", "Allied countries"], ["near_term", "long_term"],
                "armed-conflict-and-military-escalation:tech:blacksky",
                "Track imagery and analytics contracts, constellation availability, revisit rates and gross margin.", "geospatial intelligence"),
            exposure("tech-bel", "Bharat Electronics", "NSE: BEL", "positive", "supply_chain",
                "India opportunity in radar, electronic warfare, secure communications, network-centric systems and anti-drone integration; actual value depends on procurement.",
                ["The conflict highlights layered air defence and electronic-warfare needs.", "BEL has disclosed capabilities across these technology layers.", "Indian revenue requires domestic or export orders and execution."],
                ["India"], ["near_term", "long_term"], "armed-conflict-and-military-escalation:tech:bel",
                "Track product-specific orders, indigenous content, R&D-to-production conversion, order-book execution and export approvals.", "Indian defence electronics and sensor fusion"),
            exposure("tech-ideaforge", "ideaForge", "NSE: IDEAFORGE", "positive", "supply_chain",
                "India opportunity in resilient UAVs: GNSS-denied navigation, anti-jam links, thermal/SAR payloads and encrypted live video for border and maritime surveillance.",
                ["Electronic warfare can deny GPS and communications.", "Surveillance platforms need autonomous navigation and modular sensors.", "ideaForge describes these capabilities in NETRA 5; demand still requires orders."],
                ["India"], ["near_term", "long_term"], "armed-conflict-and-military-escalation:tech:ideaforge",
                "Check defence/security order intake, field trials, payload partners, service revenue, inventory and cash conversion.", "resilient UAV and ISR"),
            exposure("tech-zen", "Zen Technologies", "NSE: ZENTEC", "positive", "supply_chain",
                "India opportunity in counter-UAS sensor fusion, electronic and kinetic defeat, plus simulation for training against drone and missile threats.",
                ["Low-cost drones create a cost-asymmetry for conventional interceptors.", "Counter-UAS needs detection, classification, jamming and sometimes hard-kill response.", "Zen discloses integrated counter-drone and training products."],
                ["India", "Export markets"], ["near_term", "long_term"], "armed-conflict-and-military-escalation:tech:zen",
                "Verify awarded orders, system field performance, manufacturing scale, export licences and the split between demonstrations and delivered revenue.", "counter-drone and simulation"),
        ]
        groups = [DomainGroup(id="conflict:tech", title="Your tech & career lens", entityType="exposure", items=[
            DomainEntity(id="conflict:tech:cloud", name="Data centres and cloud operations", type="technology", direction="uncertain", magnitude="medium", summary="Energy-price volatility and regional operational risk can change hosting costs and resilience planning.", evidenceIds=evidence_ids),
            DomainEntity(id="conflict:tech:supply", name="Hardware supply chains", type="technology", direction="down", magnitude="medium", summary="Longer shipping routes and freight risk can affect delivery times and working capital for hardware-heavy businesses.", evidenceIds=evidence_ids),
            DomainEntity(id="conflict:tech:cyber", name="Cybersecurity and business continuity", type="skill", direction="up", magnitude="medium", summary="Regional escalation increases the need for monitoring, incident response and continuity planning, though specific attacks require separate evidence.", evidenceIds=evidence_ids),
        ])]
    return impact, groups


def _compose(row: dict[str, Any], rows: list[dict[str, Any]], persona: str, meta: SnapshotMeta) -> WorldShiftSnapshot:
    slug = _slug(str(row["topic"]))
    direction_raw = str(row.get("direction", "uncertain"))
    direction = _direction(direction_raw)
    priority = float(row.get("priority_score", row.get("signal_strength", 0.0)))
    signal_score = max(0.0, min(100.0, round(priority * 100, 2)))
    status = _status(str(row.get("direction_label", "")), direction_raw)
    curated_evidence = _editorial_evidence(slug)
    evidence = curated_evidence + [item for item in _evidence(row, slug) if item.id not in {entry.id for entry in curated_evidence}]
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

    # Shared knowledge path. Every shift except the frozen editorial reference
    # is composed here, from the source artifact plus its declarative knowledge
    # pack, so depth comes from the pipeline rather than from bespoke code.
    if slug != CONFLICT_ID and has_intelligence(slug):
        overview, impact, groups, relationships, forecast, evidence = compose_parts(
            slug=slug, topic=topic, category=category, persona=persona, status=status,
            peers=[(item.id, item.title) for item in related],
            observed_at=observed_date, generated_at=meta.generated_at,
        )
        return WorldShiftSnapshot(
            **meta.model_dump(), persona=persona,
            shift=ShiftOverview(
                id=slug, title=topic, summary=overview.what_happened, status=status,
                direction=direction, signalStrength=signal_score, updatedAt=observed_date,
                overview=overview, relatedShifts=related, isTrending=_is_trending(row),
            ),
            content=PersonaContent(impact=impact, domain={"groups": groups}),
            relationships=relationships, evidence=evidence, schemaVersion="2.0",
            whatHappensNext=forecast,
        )

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
    # Every shift uses the same briefing-shaped fallback. This keeps the page
    # readable even when a provider is unavailable while being explicit that
    # the source record may not establish the real-world origin of the story.
    dated_evidence = sorted(evidence, key=lambda item: item.published_at or "")
    if dated_evidence:
        earliest, latest = dated_evidence[0], dated_evidence[-1]
        earliest_detail = earliest.summary or earliest.title
        latest_detail = latest.summary or latest.title
        overview.context_brief = ContextBrief(
            whatItIs=editorial_happening,
            howItStarted=(
                f"The available source record begins on {earliest.published_at[:10]} with “{earliest.title}”. "
                f"{earliest_detail} This is the beginning of the evidence window, not necessarily the origin of the wider issue."
            ),
            latest=(f"The latest item in this evidence window is “{latest.title}”. {latest_detail}"),
            whatItIsEvidenceIds=evidence_ids[:3],
            howItStartedEvidenceIds=[earliest.id],
            latestEvidenceIds=[latest.id],
        )
        overview.timeline = [TimelineEvent(
            date=item.published_at[:10], title=item.title,
            summary=item.summary or "The source metadata records this development without a fuller extract.",
            status="reported", evidenceIds=[item.id],
        ) for item in dated_evidence[-6:]]
    bundle = editorial_bundle(slug)
    if bundle:
        overview.what_happened = bundle["summary"]
        overview.quick_take = bundle["contextBrief"]["latest"]
        overview.context_brief = ContextBrief.model_validate(bundle["contextBrief"])
        overview.timeline = [TimelineEvent.model_validate(item) for item in bundle["timeline"]]
        overview.actors = [ActorBrief.model_validate(item) for item in bundle["actors"]]
        overview.facts_and_figures = [FactFigure.model_validate(item) for item in bundle["factsAndFigures"]]
        overview.whats_happening = [IntelligencePoint(
            text=point, evidenceClass="observed", evidenceIds=evidence_ids[:5]
        ) for point in [
            "The conflict now links the Iran-US-Israel confrontation with the Yemen-Saudi and Red Sea fronts.",
            "The latest reported escalation is concentrated around Houthi attacks claimed against Saudi targets and fighting near Red Sea routes.",
            "A diplomatic channel remains open through US-Houthi talks in Oman, so escalation and de-escalation are occurring at the same time.",
        ]]
        overview.why_it_matters = "The conflict can move from a security crisis into a global economic shock through civilian displacement, energy exports and two heavily used shipping routes."
        overview.why_it_matters_points = [IntelligencePoint(
            text=text, evidenceClass="inferred", evidenceIds=ids
        ) for text, ids in [
            ("For civilians, the Yemen front is already producing displacement and creates further risk to cities and infrastructure.", [f"{slug}:brief:ap-displacement", f"{slug}:brief:ap-saudi"]),
            ("For the world economy, danger around Hormuz and Bab el-Mandeb can raise oil, shipping and insurance costs even before a route is fully closed.", [f"{slug}:brief:cfr", f"{slug}:brief:axios-talks"]),
            ("For regional stability, each new participant or retaliatory strike increases the chance that separate Iran, Yemen and Red Sea fronts become one wider conflict.", [f"{slug}:brief:cfr", f"{slug}:brief:ap-latest"]),
        ]]
        overview.key_developments = [IntelligencePoint(
            text=event["summary"], evidenceClass="observed", evidenceIds=event["evidenceIds"]
        ) for event in bundle["timeline"][-3:]]
        overview.drivers = [IntelligencePoint(text=text, evidenceClass="inferred", evidenceIds=evidence_ids[:5]) for text in [
            "The unresolved US-Iran nuclear, sanctions and regional-security confrontation.",
            "Control and safe passage through Hormuz and Bab el-Mandeb, where military risk can become an energy and trade shock.",
            "The Houthis' regional strategy and the Saudi response on the Yemen front.",
        ]]
        impact, groups = _conflict_persona_content(persona, evidence_ids[:6])
        domain_items = []
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
            overview=overview, relatedShifts=related, isTrending=_is_trending(row),
        ),
        content=PersonaContent(impact=impact, domain={"groups": groups if bundle else [DomainGroup(
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
                    status=item.shift.status, direction=item.shift.direction,
                    isTrending=item.shift.is_trending) for index, item in enumerate(snapshots, 1)],
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
            snapshot = WorldShiftSnapshot.model_validate(active.payload)
            if editorial_bundle(shift_id):
                current_rows = _latest_rows(rows)
                current_row = next((item for item in current_rows if _slug(str(item["topic"])) == shift_id), None)
                if current_row is not None:
                    editorial = _compose(current_row, current_rows, persona, SnapshotMeta(
                        snapshotId=snapshot.snapshot_id, generatedAt=snapshot.generated_at,
                        validUntil=snapshot.valid_until,
                    ))
                    snapshot.shift.summary = editorial.shift.summary
                    snapshot.shift.overview = editorial.shift.overview
                    snapshot.content = editorial.content
                    editorial_ids = {item.id for item in editorial.evidence}
                    snapshot.evidence = editorial.evidence + [item for item in snapshot.evidence if item.id not in editorial_ids]
            return snapshot
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
