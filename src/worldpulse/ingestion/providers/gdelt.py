"""GDELT provider -- global news/event coverage, no API key, no cost.

Which GDELT surface and why
---------------------------
GDELT exposes several surfaces. We use the **DOC 2.0 API**
(`https://api.gdeltproject.org/api/v2/doc/doc`) in `mode=artlist&format=json`
because:

  * it needs **no API key and no registration** (a hard requirement for
    WorldPulse's FREE mode);
  * it accepts an explicit `startdatetime`/`enddatetime` window, which is
    exactly the contract `WorldEventProvider.fetch_events` needs;
  * it returns clean JSON per article (title, url, domain, seendate,
    language, sourcecountry) with no bulk download or unzip step;
  * its query language supports the operators we care about for
    event-domain targeting -- keyword/phrase search, `domainis:`,
    `sourcecountry:`, `theme:` (GKG themes) and, importantly,
    `tone<-5` / `tone>5` for sentiment gating.

The alternatives, and why they are not the primary path:

  * **GDELT 2.0 Events (CAMEO) CSV export** --
    `http://data.gdeltproject.org/gdeltv2/<YYYYMMDDHHMMSS>.export.CSV.zip`
    (a new file every 15 minutes; index at
    `http://data.gdeltproject.org/gdeltv2/masterfilelist.txt`). This is the
    right surface for *deep* history (2015 -> present) and for structured
    CAMEO event codes, Goldstein scale and geocoded actors. It is
    deliberately not the default here because one day is ~96 zipped CSVs
    of 61 unlabeled columns: that is a bulk-ETL job, not a
    request/response adapter. `export_csv_url_for()` below builds those
    URLs so the path is available to whoever adds the bulk loader.
  * **GKG 2.0** (`.gkg.csv.zip`, same cadence) carries themes, tone and
    entity extraction, but has the same bulk-download shape.

Honest historical limitation: the DOC 2.0 API serves a rolling recent
window reliably (approximately the last 3 months). Requests for older
windows typically return an empty article list rather than an error, so
`fetch_events` logs a warning when the requested window starts more than
`DOC_API_RELIABLE_DAYS` days ago. Deeper geopolitical history needs the
CSV export path above; USGS FDSN (see `usgs.py`) is the provider to use
for genuinely deep historical backfill.

Because the DOC API is keyword-search based rather than a firehose, we
rotate through one query per event domain (conflict, military, energy
disruption, natural disaster, economic policy) across the requested
window and union the results.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlparse

import httpx

from worldpulse.config import settings
from worldpulse.events.schemas import EventDomain, WorldEvent
from worldpulse.ingestion import http_utils
from worldpulse.ingestion.providers.base import WorldEventProvider
from worldpulse.ingestion.providers.country_focus import get_focus

logger = logging.getLogger(__name__)

DOC_API_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_EXPORT_BASE = "http://data.gdeltproject.org/gdeltv2"
GDELT_MASTER_FILE_LIST = f"{GDELT_EXPORT_BASE}/masterfilelist.txt"

#: Beyond this age the DOC 2.0 API's coverage becomes unreliable.
DOC_API_RELIABLE_DAYS = 90

#: DOC 2.0 hard-caps `maxrecords` at 250.
MAX_RECORDS_CAP = 250

#: One keyword set per event domain. Terms are space-separated (implicit
#: AND in GDELT's query language) and alternates are OR'd inside
#: parentheses, which is GDELT DOC 2.0's documented syntax. `tone<-3`
#: biases towards negative/escalatory coverage for the domains where that
#: is the signal we want.
DOMAIN_QUERIES: list[tuple[EventDomain, str, str, list[str]]] = [
    (
        EventDomain.CONFLICT,
        "conflict_geopolitical",
        '("armed clashes" OR insurgency OR "ceasefire collapse" OR '
        '"state of emergency" OR coup OR "border conflict") tone<-3',
        ["shipping_lanes", "regional_security", "diplomatic_relations"],
    ),
    (
        EventDomain.MILITARY,
        "military_activity",
        '(airstrike OR "missile strike" OR "troop deployment" OR '
        '"naval clash" OR "military offensive" OR drone strike) tone<-3',
        ["regional_security", "shipping_lanes"],
    ),
    (
        EventDomain.ENERGY,
        "energy_disruption",
        '("pipeline explosion" OR "refinery fire" OR "oil production cut" OR '
        '"tanker attacked" OR "gas supply halted" OR "export terminal shut")',
        ["energy_supply", "shipping_lanes", "supply_chain"],
    ),
    (
        EventDomain.DISASTER,
        "natural_disaster",
        '(earthquake OR "volcanic eruption" OR typhoon OR hurricane OR '
        '"flash flooding" OR wildfire) (damage OR evacuation OR casualties)',
        ["infrastructure", "supply_chain"],
    ),
    (
        EventDomain.ECONOMIC,
        "economic_policy",
        '("interest rate decision" OR "central bank" OR "new sanctions" OR '
        '"export ban" OR "inflation data" OR "emergency rate")',
        ["monetary_policy", "trade_policy"],
    ),
]

#: Coarse severity prior per domain -- GDELT gives us no magnitude, so the
#: rule-based classifier refines this downstream. Kept mid-range so a news
#: article never outranks a magnitude-7 earthquake on severity alone.
_DOMAIN_SEVERITY_PRIOR: dict[EventDomain, float] = {
    EventDomain.CONFLICT: 0.55,
    EventDomain.MILITARY: 0.60,
    EventDomain.ENERGY: 0.58,
    EventDomain.DISASTER: 0.55,
    EventDomain.ECONOMIC: 0.45,
}

#: Country name fragments we can cheaply recover from an article title.
#: (GDELT DOC artlist gives `sourcecountry` -- the *publisher's* country --
#: not the event's country, so titles are the better signal here.)
_COUNTRY_HINTS: dict[str, str] = {
    "united states": "USA", "u.s.": "USA", "washington": "USA", "america": "USA",
    "russia": "Russia", "moscow": "Russia", "ukraine": "Ukraine", "kyiv": "Ukraine",
    "israel": "Israel", "gaza": "Israel", "iran": "Iran", "tehran": "Iran",
    "china": "China", "beijing": "China", "taiwan": "Taiwan", "taipei": "Taiwan",
    "japan": "Japan", "tokyo": "Japan", "saudi": "Saudi Arabia", "riyadh": "Saudi Arabia",
    "venezuela": "Venezuela", "north korea": "North Korea", "south korea": "South Korea",
    "india": "India", "pakistan": "Pakistan", "turkey": "Turkey", "egypt": "Egypt",
    "nigeria": "Nigeria", "libya": "Libya", "iraq": "Iraq", "syria": "Syria",
    "yemen": "Yemen", "lebanon": "Lebanon", "germany": "Germany", "france": "France",
    "united kingdom": "United Kingdom", "britain": "United Kingdom", "london": "United Kingdom",
    "poland": "Poland", "mexico": "Mexico", "brazil": "Brazil", "indonesia": "Indonesia",
    "philippines": "Philippines", "australia": "Australia", "canada": "Canada",
}


def _fmt_gdelt_datetime(value: datetime) -> str:
    """GDELT wants `YYYYMMDDHHMMSS` in UTC."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S")


def parse_seendate(raw: str) -> Optional[datetime]:
    """Parse GDELT's `seendate`, e.g. `20240115T123000Z`.

    Also tolerates the plain `YYYYMMDDHHMMSS` and ISO forms that appear in
    some GDELT responses.
    """
    if not raw:
        return None
    raw = raw.strip()
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%d%H%M%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        logger.debug("gdelt: unparseable seendate %r", raw)
        return None


def export_csv_url_for(slot: datetime) -> str:
    """URL of the GDELT 2.0 Events CSV export covering `slot`.

    Files land every 15 minutes on the UTC quarter-hour. Provided for the
    deep-history bulk path documented in this module's docstring; not used
    by `fetch_events`.
    """
    if slot.tzinfo is None:
        slot = slot.replace(tzinfo=timezone.utc)
    slot = slot.astimezone(timezone.utc).replace(second=0, microsecond=0)
    slot = slot.replace(minute=(slot.minute // 15) * 15)
    return f"{GDELT_EXPORT_BASE}/{slot.strftime('%Y%m%d%H%M%S')}.export.CSV.zip"


class GDELTProvider(WorldEventProvider):
    """GDELT DOC 2.0 API adapter. No key, no cost, no registration."""

    name = "gdelt"
    requires_key = False
    is_paid = False

    def __init__(
        self,
        client: Optional[httpx.Client] = None,
        max_records: int | None = None,
        english_only: bool = True,
    ) -> None:
        super().__init__()
        self._client = client
        self._max_records = min(
            MAX_RECORDS_CAP, max_records if max_records is not None else settings.gdelt_max_records
        )
        self._english_only = english_only

    # --- WorldEventProvider -------------------------------------------

    def fetch_events(self, start_time: datetime, end_time: datetime) -> list[WorldEvent]:
        events, _ = self._timed(self._fetch, start_time, end_time)
        return events

    def _fetch(self, start_time: datetime, end_time: datetime) -> list[WorldEvent]:
        age_days = (datetime.now(timezone.utc) - start_time.astimezone(timezone.utc)).days
        if age_days > DOC_API_RELIABLE_DAYS:
            logger.warning(
                "gdelt: requested window starts %d days ago; the DOC 2.0 API only serves "
                "~%d days reliably and will likely return few/no articles. Use the GDELT "
                "Events CSV export for deeper history.",
                age_days, DOC_API_RELIABLE_DAYS,
            )

        focus = get_focus()
        by_url: dict[str, WorldEvent] = {}
        errors: list[str] = []
        for domain, domain_label, query, channels in DOMAIN_QUERIES:
            focused_query = f"{query} sourcecountry:{focus.gdelt_fips}" if focus else query
            try:
                articles = self._query_articles(focused_query, start_time, end_time)
            except Exception as exc:  # noqa: BLE001 - one query failing must not kill the rest
                errors.append(f"{domain_label}: {exc}")
                logger.warning("gdelt: query for %s failed: %s", domain_label, exc)
                continue
            for article in articles:
                event = self._article_to_event(article, domain, channels, focused_query)
                if event is None:
                    continue
                # A single article can match several domain queries; keep
                # the first (query order = descending market relevance).
                key = event.provider_event_id
                if key not in by_url:
                    by_url[key] = event

        if not by_url and errors:
            raise http_utils.ProviderHTTPError(
                "gdelt: every domain query failed: " + "; ".join(errors[:3])
            )
        events = sorted(by_url.values(), key=lambda e: e.occurred_at)
        logger.info("gdelt: %d articles mapped to events for %s..%s",
                    len(events), start_time.isoformat(), end_time.isoformat())
        return events

    # --- HTTP ----------------------------------------------------------

    def _query_articles(self, query: str, start_time: datetime, end_time: datetime) -> list[dict[str, Any]]:
        params = {
            "query": query,
            "mode": "artlist",
            "format": "json",
            "maxrecords": self._max_records,
            "sort": "datedesc",
            "startdatetime": _fmt_gdelt_datetime(start_time),
            "enddatetime": _fmt_gdelt_datetime(end_time),
        }
        payload = http_utils.http_get_json(DOC_API_URL, params=params, client=self._client)
        if not isinstance(payload, dict):
            return []
        articles = payload.get("articles") or []
        return [a for a in articles if isinstance(a, dict)]

    # --- Mapping -------------------------------------------------------

    def _article_to_event(
        self,
        article: dict[str, Any],
        domain: EventDomain,
        channels: list[str],
        query: str,
    ) -> Optional[WorldEvent]:
        url = (article.get("url") or "").strip()
        title = (article.get("title") or "").strip()
        if not url or not title:
            return None
        if self._english_only:
            language = (article.get("language") or "").strip().lower()
            # DOC artlist reports full language names ("English"); accept
            # blanks so we never drop everything if the field is absent.
            if language and language not in ("english", "eng", "en"):
                return None

        occurred_at = parse_seendate(article.get("seendate") or "")
        if occurred_at is None:
            return None

        domain_name = (article.get("domain") or urlparse(url).netloc or "").strip()
        now = datetime.now(timezone.utc)
        countries = self._countries_from_title(title, article.get("sourcecountry"))

        return WorldEvent(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"worldpulse-gdelt:{url}")),
            provider=self.name,
            provider_event_id=url,
            source_id=f"gdelt:{url}",
            occurred_at=occurred_at,
            ingested_at=now,
            first_seen_at=now,
            event_type=domain,
            event_subtype=_subtype_from_title(title),
            event_subtype_detail=f"gdelt-query:{query[:60]}",
            headline=title,
            summary="",
            countries=countries,
            locations=[],
            entities=[e for e in countries],
            affected_channels=list(channels),
            potential_assets=[],  # the classifier/impact-channel layer fills this
            severity=_DOMAIN_SEVERITY_PRIOR.get(domain, 0.5),
            # A single news article is one source: weaker than an
            # instrumented feed like USGS, hence the modest confidence.
            source_confidence=0.6,
            corroboration_count=1,
            source_urls=[url],
            source_name=domain_name,
            reasoning_summary=(
                f"GDELT DOC 2.0 article from {domain_name or 'unknown domain'} matched the "
                f"{domain.value} keyword set; occurred_at taken from GDELT `seendate`."
            ),
            raw_payload=dict(article),
        )

    @staticmethod
    def _countries_from_title(title: str, source_country: Any) -> list[str]:
        lower = title.lower()
        found: list[str] = []
        for fragment, canonical in _COUNTRY_HINTS.items():
            if fragment in lower and canonical not in found:
                found.append(canonical)
        if not found and isinstance(source_country, str) and source_country.strip():
            found.append(source_country.strip())
        return found[:4]


#: Headline keyword -> granular event type. Deliberately shares vocabulary
#: with `events.classifier._SUBTYPE_KEYWORDS` so both layers agree.
_TITLE_SUBTYPES: list[tuple[str, tuple[str, ...]]] = [
    ("earthquake", ("earthquake", "quake", "magnitude")),
    ("volcanic_eruption", ("volcano", "volcanic", "eruption")),
    ("storm", ("hurricane", "typhoon", "cyclone", "storm")),
    ("flooding", ("flood", "flash flooding")),
    ("wildfire", ("wildfire", "bushfire", "forest fire")),
    ("missile_strike", ("missile", "airstrike", "air strike", "drone strike")),
    ("naval_incident", ("naval", "tanker", "warship", "strait")),
    ("troop_movement", ("troop", "deployment", "mobilisation", "mobilization")),
    ("pipeline_disruption", ("pipeline",)),
    ("refinery_disruption", ("refinery",)),
    ("production_cut", ("production cut", "output cut", "opec")),
    ("shipping_disruption", ("shipping", "port closed", "export terminal")),
    ("rate_decision", ("interest rate", "rate decision", "central bank", "rate hike", "rate cut")),
    ("sanctions", ("sanction", "export ban", "embargo")),
    ("inflation_shock", ("inflation", "cpi")),
    ("ceasefire_breakdown", ("ceasefire",)),
    ("state_of_emergency", ("state of emergency",)),
    ("armed_clash", ("clash", "insurgen", "offensive", "coup")),
]


def _subtype_from_title(title: str) -> str:
    lower = title.lower()
    for subtype, keywords in _TITLE_SUBTYPES:
        if any(kw in lower for kw in keywords):
            return subtype
    return "general"
