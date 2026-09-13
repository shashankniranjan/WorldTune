"""Loader/evaluator for `config/impact_channels.yaml`.

The event -> asset/channel/industry/commodity mapping used to be hardcoded
in `events/classifier.py` as a per-domain dict. The multi-provider
refactor moved it into a declarative YAML table so that the many new event
subtypes (earthquake, tropical_cyclone, wildfire, volcanic_eruption,
armed_clash, ...) can be mapped without code changes, and so a
region-specific rule ("earthquake + Taiwan -> semiconductor ETF") can be
expressed at all.

The hardcoded per-domain table survives as `defaults:` inside the YAML,
and as `_FALLBACK_DEFAULTS` here, so behaviour is unchanged when the YAML
is missing or PyYAML is unavailable.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Optional

from worldpulse.config import settings
from worldpulse.events.schemas import EventDomain, WorldEvent

logger = logging.getLogger(__name__)

#: Used when config/impact_channels.yaml is absent or unreadable. Mirrors
#: the pre-refactor `_DOMAIN_ASSETS` / `_DOMAIN_MARKET_RELEVANCE` tables
#: exactly, so removing the YAML degrades to the old behaviour rather than
#: to nothing.
_FALLBACK_DEFAULTS: dict[str, dict[str, Any]] = {
    "conflict_geopolitical": {
        "assets": ["GC=F", "^VIX", "^GSPC", "BZ=F", "DX-Y.NYB"],
        "channels": ["regional_security", "diplomatic_relations"],
        "market_relevance": 0.75,
    },
    "military_activity": {
        "assets": ["GC=F", "^VIX", "BZ=F", "CL=F", "ITA", "^GSPC"],
        "channels": ["regional_security", "shipping_lanes"],
        "market_relevance": 0.80,
    },
    "energy_disruption": {
        "assets": ["BZ=F", "CL=F", "NG=F", "XLE", "^GSPC"],
        "channels": ["energy_supply", "shipping_lanes"],
        "market_relevance": 0.85,
    },
    "economic_policy": {
        "assets": ["DX-Y.NYB", "^GSPC", "^IXIC", "TLT", "EURUSD=X"],
        "channels": ["monetary_policy", "trade_policy"],
        "market_relevance": 0.70,
    },
    "natural_disaster": {
        "assets": ["^GSPC", "GC=F", "TLT", "XLE"],
        "channels": ["infrastructure", "supply_chain"],
        "market_relevance": 0.55,
    },
}


@dataclass
class ImpactMapping:
    """Result of evaluating the mapping table against one event."""

    assets: list[str] = field(default_factory=list)
    channels: list[str] = field(default_factory=list)
    industries: list[str] = field(default_factory=list)
    commodities: list[str] = field(default_factory=list)
    market_relevance: float = 0.5
    matched_rules: list[str] = field(default_factory=list)


@dataclass
class ImpactChannelTable:
    """Parsed mapping table."""

    regions: dict[str, list[str]] = field(default_factory=dict)
    defaults: dict[str, dict[str, Any]] = field(default_factory=dict)
    rules: list[dict[str, Any]] = field(default_factory=list)
    source_path: Optional[str] = None

    # --- evaluation ----------------------------------------------------

    def resolve(self, event: WorldEvent) -> ImpactMapping:
        domain = _domain_of(event)
        subtype = (event.event_subtype or "").strip().lower()
        haystack = " ".join(filter(None, [
            event.headline, event.summary, " ".join(event.locations),
            event.event_subtype_detail,
        ])).lower()
        place_tokens = _place_tokens(event)

        assets: list[str] = []
        channels: list[str] = []
        industries: list[str] = []
        commodities: list[str] = []
        matched: list[str] = []
        relevance = 0.0

        for rule in self.rules:
            if not self._rule_matches(rule, domain, subtype, haystack, place_tokens, event):
                continue
            matched.append(str(rule.get("name") or "unnamed"))
            _extend_unique(assets, rule.get("assets") or [])
            _extend_unique(channels, rule.get("channels") or [])
            _extend_unique(industries, rule.get("industries") or [])
            _extend_unique(commodities, rule.get("commodities") or [])
            relevance = max(relevance, float(rule.get("market_relevance") or 0.0))

        if not matched:
            default = self.defaults.get(domain) or _FALLBACK_DEFAULTS.get(domain) or {}
            _extend_unique(assets, default.get("assets") or [])
            _extend_unique(channels, default.get("channels") or [])
            _extend_unique(industries, default.get("industries") or [])
            _extend_unique(commodities, default.get("commodities") or [])
            relevance = float(default.get("market_relevance") or 0.5)
            if default:
                matched.append(f"default:{domain}")

        return ImpactMapping(
            assets=assets,
            channels=channels,
            industries=industries,
            commodities=commodities,
            market_relevance=round(max(0.0, min(1.0, relevance or 0.5)), 4),
            matched_rules=matched,
        )

    def market_relevance(self, domain: EventDomain | str) -> float:
        """Per-domain historical market relevance prior."""
        key = domain.value if hasattr(domain, "value") else str(domain)
        source = self.defaults.get(key) or _FALLBACK_DEFAULTS.get(key) or {}
        return float(source.get("market_relevance") or 0.5)

    def region_members(self, region: str) -> list[str]:
        return list(self.regions.get(region) or [])

    # --- matching ------------------------------------------------------

    def _rule_matches(
        self,
        rule: dict[str, Any],
        domain: str,
        subtype: str,
        haystack: str,
        place_tokens: set[str],
        event: WorldEvent,
    ) -> bool:
        domains = _as_str_list(rule.get("domains"))
        if domains and domain not in {d.lower() for d in domains}:
            return False

        subtypes = _as_str_list(rule.get("subtypes"))
        if subtypes and subtype not in {s.lower() for s in subtypes}:
            return False

        countries = _as_str_list(rule.get("countries"))
        if countries and not any(c.lower() in place_tokens for c in countries):
            return False

        regions = _as_str_list(rule.get("regions"))
        if regions:
            members: set[str] = set()
            for region in regions:
                members.update(m.lower() for m in self.region_members(region))
            if not any(member in place_tokens for member in members):
                return False

        keywords = _as_str_list(rule.get("keywords"))
        if keywords and not any(k.lower() in haystack for k in keywords):
            return False

        min_severity = rule.get("min_severity")
        if min_severity is not None and event.severity < float(min_severity):
            return False

        # A rule with no conditions at all would match everything; treat
        # that as a config error and ignore it.
        return bool(domains or subtypes or countries or regions or keywords
                    or min_severity is not None)


# --- loading ------------------------------------------------------------

def _candidate_paths(path: str | None) -> list[str]:
    configured = path or settings.impact_channels_path
    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(here, "..", "..", ".."))
    return [
        configured,
        os.path.join(os.getcwd(), configured),
        os.path.join(repo_root, configured),
        os.path.join(repo_root, "config", "impact_channels.yaml"),
    ]


def load_table(path: str | None = None) -> ImpactChannelTable:
    """Load the mapping table, degrading to the built-in defaults."""
    try:
        import yaml  # type: ignore
    except ImportError:  # pragma: no cover - PyYAML is a declared dependency
        logger.warning("impact_channels: PyYAML unavailable; using built-in defaults")
        return ImpactChannelTable(defaults=dict(_FALLBACK_DEFAULTS))

    for candidate in _candidate_paths(path):
        if not candidate or not os.path.isfile(candidate):
            continue
        try:
            with open(candidate, "r", encoding="utf-8") as handle:
                payload = yaml.safe_load(handle) or {}
        except Exception as exc:  # noqa: BLE001
            logger.warning("impact_channels: failed to read %s: %s", candidate, exc)
            continue
        if not isinstance(payload, dict):
            continue
        table = ImpactChannelTable(
            regions={
                str(k): _as_str_list(v)
                for k, v in (payload.get("regions") or {}).items()
            },
            defaults={
                str(k): dict(v) for k, v in (payload.get("defaults") or {}).items()
                if isinstance(v, dict)
            },
            rules=[r for r in (payload.get("rules") or []) if isinstance(r, dict)],
            source_path=candidate,
        )
        if not table.defaults:
            table.defaults = dict(_FALLBACK_DEFAULTS)
        logger.info("impact_channels: loaded %d rules from %s", len(table.rules), candidate)
        return table

    logger.info("impact_channels: no YAML found on %s; using built-in defaults",
                settings.impact_channels_path)
    return ImpactChannelTable(defaults=dict(_FALLBACK_DEFAULTS))


@lru_cache(maxsize=4)
def _cached_table(path: str | None) -> ImpactChannelTable:
    return load_table(path)


def get_table(path: str | None = None) -> ImpactChannelTable:
    """Process-wide cached mapping table."""
    return _cached_table(path)


def reset_cache() -> None:
    """Test helper: force the YAML to be re-read."""
    _cached_table.cache_clear()


# --- helpers ------------------------------------------------------------

def _domain_of(event: WorldEvent) -> str:
    value = event.event_domain or event.event_type
    return (value.value if hasattr(value, "value") else str(value)).strip().lower()


def _place_tokens(event: WorldEvent) -> set[str]:
    """Lowercased country/location strings for substring region matching."""
    tokens: set[str] = set()
    for value in list(event.countries) + list(event.locations) + list(event.entities):
        text = str(value).strip().lower()
        if text:
            tokens.add(text)
            # A USGS `place` like "14 km sse of hualien city, taiwan" must
            # match the country rule for "Taiwan".
            for part in text.replace(";", ",").split(","):
                part = part.strip()
                if part:
                    tokens.add(part)
    # Also allow matching against the headline, which is where GDELT
    # carries the country name.
    headline = (event.headline or "").lower()
    return _SubstringSet(tokens, headline)


class _SubstringSet(set):
    """Set whose `in` test also succeeds on a headline substring match.

    `"taiwan" in place_tokens` must be True both when Taiwan is an
    explicit country (USGS/GDACS) and when it only appears in the headline
    (GDELT), without forcing every rule to be written twice.
    """

    def __new__(cls, values, haystack: str):
        obj = super().__new__(cls, values)
        return obj

    def __init__(self, values, haystack: str):
        super().__init__(values)
        self._haystack = haystack

    def __contains__(self, item: object) -> bool:  # type: ignore[override]
        text = str(item).lower().strip()
        if not text:
            return False
        if super().__contains__(text):
            return True
        pattern = re.compile(rf"(?<![a-z]){re.escape(text)}(?![a-z])")
        # Word-boundary matching only, so "India" does not match "Indiana"
        # and "Oman" does not match "Romania".
        if any(pattern.search(token) for token in self):
            return True
        return bool(self._haystack) and bool(pattern.search(self._haystack))


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        return [str(v) for v in value if v is not None]
    return []


def _extend_unique(target: list[str], values: Any) -> None:
    for value in _as_str_list(values):
        if value not in target:
            target.append(value)
