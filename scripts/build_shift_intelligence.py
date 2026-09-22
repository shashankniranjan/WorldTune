#!/usr/bin/env python3
"""Build the per-World-Shift intelligence artifact that the contract composer reads.

The gold artifact (``build_world_shifts.py``) answers "is this topic moving?".
It deliberately keeps only ten alphabetically-selected source records, which is
enough to rank a shift but far too thin to brief a reader on it.

This builder answers the second question -- "what is actually in the reporting?"
-- for every shift on the published date:

* source records chosen for publisher standing, headline informativeness and
  de-syndication rather than alphabetical domain order,
* a readable headline recovered from the publisher URL when the source record
  carries no title,
* entity, place and theme rollups cleaned of provider offset encoding,
* a daily attention series so the composer can date the story instead of
  asserting an origin it cannot see.

Nothing here interprets the shift. Interpretation lives in
``app/services/world_shift_knowledge.py`` (declarative, per topic) and
``app/services/world_shift_intelligence.py`` (one generic composer).
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTICLES = ROOT / "data/processed/worldtune/layers/silver_articles.parquet"
DEFAULT_SHIFTS = ROOT / "data/processed/worldtune/world_shifts/gold_world_shifts.parquet"
DEFAULT_OUT = ROOT / "data/processed/worldtune/world_shifts/shift_intelligence.json"

# Imported rather than duplicated so the artifact can never drift from the
# detector that produced the shift in the first place.
import importlib.util

_spec = importlib.util.spec_from_file_location("_bws", Path(__file__).with_name("build_world_shifts.py"))
_bws = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_bws)
DETECTORS = _bws.DETECTORS

EVIDENCE_PER_SHIFT = 24
SERIES_DAYS = 14

# Publisher standing tiers. This is an editorial judgement about reporting
# provenance -- wire services and named desks over content farms and
# syndication mirrors -- not a quality claim about any individual article.
TIER_ONE = {
    "reuters.com", "apnews.com", "bloomberg.com", "ft.com", "wsj.com", "nytimes.com",
    "washingtonpost.com", "bbc.com", "bbc.co.uk", "theguardian.com", "economist.com",
    "cnbc.com", "afp.com", "aljazeera.com", "npr.org", "politico.com", "axios.com",
    "nikkei.com", "scmp.com", "thehindu.com", "business-standard.com", "livemint.com",
    "economictimes.indiatimes.com", "moneycontrol.com", "hindustantimes.com",
    "indianexpress.com", "thehindubusinessline.com", "reutersagency.com",
}
TIER_TWO = {
    "cnn.com", "abcnews.go.com", "cbsnews.com", "nbcnews.com", "theverge.com",
    "arstechnica.com", "wired.com", "techcrunch.com", "zdnet.com", "theregister.com",
    "tomshardware.com", "anandtech.com", "semianalysis.com", "protocol.com",
    "bleepingcomputer.com", "krebsonsecurity.com", "securityweek.com", "darkreading.com",
    "coindesk.com", "cointelegraph.com", "theblock.co", "barrons.com", "marketwatch.com",
    "investing.com", "fortune.com", "forbes.com", "businessinsider.com", "yahoo.com",
    "spglobal.com", "oilprice.com", "argusmedia.com", "platts.com", "defensenews.com",
    "breakingdefense.com", "janes.com", "digitimes.com", "eetimes.com", "datacenterdynamics.com",
    "aninews.in", "pymnts.com", "finextra.com", "medianama.com", "entrackr.com",
}
# Domains whose output in this corpus is overwhelmingly rewrapped wire copy.
SYNDICATION_MARKERS = re.compile(
    r"(news|sun|leader|times|post|herald|mirror|star|daily|today|report)\.net$"
    r"|^(www\.)?(afghanistan|bangladesh|africa|asia|europe|latin|pakistan|srilanka|nepal|bhutan)",
    re.I,
)

# Slug fragments that are routing, not headline.
SLUG_NOISE = re.compile(
    r"^(news|article|articles|story|stories|p|ixp|en|in|us|uk|world|business|technology|tech|"
    r"markets|money|politics|insights|blog|posts?|amp|index|content|feed|20\d{2}|\d{1,2}|\d{5,})$",
    re.I,
)
ACRONYMS = {
    "ai", "us", "uk", "eu", "un", "sec", "cftc", "fbi", "cia", "nsa", "irs", "gdp", "cpi",
    "rbi", "upi", "sebi", "gst", "npci", "iot", "api", "apis", "gpu", "gpus", "cpu", "cpus",
    "hbm", "tsmc", "asml", "amd", "ibm", "aws", "gcp", "sap", "llm", "llms", "ml", "nlp",
    "ceo", "cfo", "cto", "ciso", "it", "hr", "ipo", "etf", "etfs", "nft", "nfts", "defi",
    "dao", "btc", "eth", "xrp", "usd", "inr", "eur", "jpy", "cny", "opec", "nato", "imf",
    "boj", "ecb", "fed", "fomc", "pmla", "fiu", "occ", "fdic", "ftc", "fcc", "doj", "dod",
    "sk", "lg", "nvidia", "openai", "5g", "6g", "ev", "evs", "saas", "paas", "iaas",
    "ransomware", "ddos", "vpn", "mfa", "sso", "ssd", "ram", "chatgpt", "pc", "pcs",
}
FORCE_CASE = {
    "nvidia": "Nvidia", "openai": "OpenAI", "chatgpt": "ChatGPT", "tsmc": "TSMC",
    "asml": "ASML", "sk": "SK", "hynix": "Hynix", "deepseek": "DeepSeek",
    "anthropic": "Anthropic", "microsoft": "Microsoft", "google": "Google",
    "amazon": "Amazon", "apple": "Apple", "meta": "Meta", "intel": "Intel",
    "samsung": "Samsung", "ransomware": "ransomware", "ddos": "DDoS",
}

# Provider theme codes carry the analytic value; their raw form is internal
# vocabulary and never reaches a reader. Only codes with an unambiguous
# plain-English reading are mapped -- everything else is dropped.
THEME_LABELS = {
    "ECON_INFLATION": "inflation",
    "ECON_INTEREST_RATES": "interest rates",
    "WB_442_INFLATION": "inflation",
    "ECON_STOCKMARKET": "equity markets",
    "ECON_OILPRICE": "oil prices",
    "ECON_DIESELPRICE": "fuel prices",
    "ECON_CENTRALBANK": "central-bank policy",
    "EPU_POLICY": "policy uncertainty",
    "EPU_ECONOMY": "economic outlook",
    "EPU_CATS_NATIONAL_SECURITY": "national security",
    "EPU_CATS_REGULATION": "regulation",
    "EPU_CATS_TRADE_POLICY": "trade policy",
    "EPU_CATS_TAXES": "taxation",
    "WB_698_TRADE": "trade",
    "WB_507_ENERGY_AND_EXTRACTIVES": "energy and extractives",
    "WB_539_OIL_AND_GAS_POLICY_STRATEGY_AND_INSTITUTIONS": "oil and gas policy",
    "WB_2298_REFINERIES": "refining",
    "WB_1104_MACROECONOMIC_VULNERABILITY_AND_DEBT": "macroeconomic vulnerability and debt",
    "WB_2433_CONFLICT_AND_VIOLENCE": "conflict and violence",
    "WB_2462_POLITICAL_VIOLENCE_AND_WAR": "political violence and war",
    "WB_678_DIGITAL_GOVERNMENT": "digital government",
    "WB_2024_ANTI_CORRUPTION_AUTHORITIES": "anti-corruption enforcement",
    "WB_1467_EDUCATION_FOR_ALL": "education access",
    "WB_470_EMPLOYMENT_AND_LABOR_MARKETS": "employment and labour markets",
    "WB_2670_JOBS": "jobs",
    "WB_2679_LABOR_MARKET_POLICY_AND_PROGRAMS": "labour-market policy",
    "TAX_ECON_PRICE": "prices",
    "ARMEDCONFLICT": "armed conflict",
    "CEASEFIRE": "ceasefire",
    "SANCTIONS": "sanctions",
    "TRIAL": "legal proceedings",
    "LEGISLATION": "legislation",
    "CYBER_ATTACK": "cyber attack",
    "DRONES": "drones",
    "MANUFACTURING": "manufacturing",
    "SCIENCE": "research and science",
    "PRIVACY": "privacy",
    "SURVEILLANCE": "surveillance",
    "GENERAL_GOVERNMENT": "government action",
    "USPEC_POLICY1": "policy debate",
    "MEDIA_CENSORSHIP": "content regulation",
    "TAX_DISEASE": "public health",
    "ENV_CLIMATECHANGE": "climate",
    "ENV_NUCLEARPOWER": "nuclear power",
    "SELF_IDENTIFIED_ENVIRON_DISASTER": "environmental disaster",
    "CRISISLEX_CRISISLEXREC": "crisis response",
    "WB_2745_FINANCIAL_SECTOR_DEVELOPMENT": "financial-sector development",
    "WB_1235_CENTRAL_BANKS": "central banks",
    "WB_1236_MONETARY_POLICY": "monetary policy",
    "WB_1729_PAYMENT_SYSTEMS": "payment systems",
    "WB_2457_FINANCIAL_CRIMES": "financial crime",
    "WB_1741_FINANCIAL_INCLUSION": "financial inclusion",
    "WB_1776_GOVERNMENT_FINANCIAL_MANAGEMENT": "public financial management",
    "WB_2670_JOBS_DIAGNOSTICS": "labour-market diagnostics",
    "TAX_TERROR_GROUP": "designated groups",
    "MILITARY": "military activity",
    "SECURITY_SERVICES": "security services",
    "NUCLEAR": "nuclear programmes",
}


def _clean_entity(value: str) -> str:
    """Strip provider offset encoding (``2#Iowa, United States#US#…#855``)."""
    text = str(value or "").strip()
    if not text:
        return ""
    parts = [part for part in text.split("#") if part]
    for part in parts:
        candidate = part.strip()
        if not candidate or candidate.isdigit():
            continue
        if re.fullmatch(r"-?\d+(\.\d+)?", candidate):
            continue
        if len(candidate) < 2 or len(candidate) > 60:
            continue
        if re.fullmatch(r"[A-Z0-9]{2,6}", candidate) and " " not in candidate:
            continue  # country/FIPS code, not a readable name
        return candidate
    return ""


def _rollup(series: pd.Series, limit: int) -> list[str]:
    counter: Counter[str] = Counter()
    for raw in series.fillna("").astype(str):
        if not raw:
            continue
        for chunk in raw.split(";"):
            name = _clean_entity(chunk)
            if name:
                counter[name] += 1
    return [name for name, _ in counter.most_common(limit)]


def _themes(series: pd.Series, limit: int) -> list[str]:
    counter: Counter[str] = Counter()
    for raw in series.fillna("").astype(str):
        for code in raw.split(";"):
            label = THEME_LABELS.get(code.strip())
            if label:
                counter[label] += 1
    return [label for label, _ in counter.most_common(limit)]


def _slug_words(url: str) -> list[str]:
    path = re.sub(r"[?#].*$", "", str(url or "")).rstrip("/")
    segments = [segment for segment in path.split("/")[3:] if segment]
    if not segments:
        return []
    best: list[str] = []
    for segment in segments:
        segment = re.sub(r"\.(html?|php|aspx?|amp)$", "", segment, flags=re.I)
        words = [word for word in re.split(r"[-_+]+", segment) if word and not SLUG_NOISE.fullmatch(word)]
        words = [word for word in words if not re.fullmatch(r"\d+", word)]
        if len(words) > len(best):
            best = words
    return best


def _headline(url: str, title: str) -> str:
    existing = str(title or "").strip()
    if len(existing) > 12:
        return existing
    words = _slug_words(url)
    if len(words) < 3:
        return ""
    out: list[str] = []
    for index, word in enumerate(words):
        lower = word.lower()
        if lower in FORCE_CASE:
            out.append(FORCE_CASE[lower])
        elif lower in ACRONYMS:
            out.append(lower.upper() if len(lower) <= 5 else lower.capitalize())
        elif index == 0:
            out.append(word.capitalize())
        else:
            out.append(lower)
    text = " ".join(out)
    text = re.sub(r"\bs\b", "", text).strip()
    return text[:1].upper() + text[1:]


def _tier(domain: str) -> int:
    domain = domain.lower().removeprefix("www.")
    if domain in TIER_ONE:
        return 0
    if domain in TIER_TWO:
        return 1
    if SYNDICATION_MARKERS.search(domain):
        return 3
    return 2


def _select_evidence(matched: pd.DataFrame, pattern: str, limit: int) -> list[dict]:
    """Pick source records by publisher standing and headline substance.

    The gold artifact takes the alphabetically first domain per shift, which
    reliably surfaces mirror sites. Here each domain contributes at most one
    record, records are ranked by tier then by how much of the detector
    vocabulary the recovered headline actually carries, and near-duplicate
    headlines (the same wire story rewrapped) are collapsed.
    """
    detector = re.compile(pattern, re.I)
    candidates: list[dict] = []
    seen_domains: set[str] = set()
    rows = matched.to_dict("records")
    for row in rows:
        url = str(row.get("url") or "")
        domain = str(row.get("domain") or "").lower().removeprefix("www.")
        if not url.startswith(("http://", "https://")) or not domain:
            continue
        headline = _headline(url, row.get("title"))
        if not headline or len(headline) < 20:
            continue
        candidates.append({
            "url": url,
            "domain": domain,
            "title": headline,
            "tier": _tier(domain),
            "hits": len(detector.findall(headline)),
            "length": len(headline),
            "publishedAt": str(row.get("published_at") or "")[:19],
            "themes": _themes(pd.Series([row.get("themes")]), 4),
        })
    candidates.sort(key=lambda item: (item["tier"], -item["hits"], -min(item["length"], 110)))
    selected: list[dict] = []
    seen_shapes: set[str] = set()
    for item in candidates:
        if item["domain"] in seen_domains:
            continue
        shape = " ".join(sorted(re.findall(r"[a-z]{4,}", item["title"].lower()))[:9])
        if shape in seen_shapes:
            continue
        seen_domains.add(item["domain"])
        seen_shapes.add(shape)
        selected.append(item)
        if len(selected) >= limit:
            break
    return selected


def build(articles_path: Path, shifts_path: Path, out: Path) -> dict:
    shifts = pd.read_parquet(shifts_path)
    shifts["date"] = pd.to_datetime(shifts["date"], utc=True)
    latest = shifts[shifts.date == shifts.date.max()]

    columns = ["date", "published_at", "domain", "url", "title", "themes", "persons",
               "organizations", "locations", "source_quality"]
    articles = pd.read_parquet(articles_path, columns=columns)
    articles["date"] = pd.to_datetime(articles["date"], utc=True)
    text = articles["url"].fillna("").astype(str).str.lower() + " " + articles["title"].fillna("").astype(str).str.lower()
    articles["_search_text"] = text

    published = str(latest.date.max().date())
    window_start = latest.date.max() - pd.Timedelta(days=SERIES_DAYS - 1)

    result: dict[str, dict] = {}
    for row in latest.to_dict("records"):
        topic = str(row["topic"])
        category = str(row["category"])
        pattern = DETECTORS.get(category, {}).get(topic)
        if not pattern:
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
        flag = f"topic_{category}"
        pool = articles[articles[flag].eq(True)] if flag in articles else articles
        matched = pool[pool["_search_text"].str.contains(pattern, regex=True, na=False)]
        day = matched[matched.date == row["date"]]
        window = matched[(matched.date >= window_start) & (matched.date <= row["date"])]

        series = (window.groupby(window.date.dt.strftime("%Y-%m-%d")).size()
                  .reindex(pd.date_range(window_start, row["date"], freq="D").strftime("%Y-%m-%d"),
                           fill_value=0))
        domain_series = (window.groupby(window.date.dt.strftime("%Y-%m-%d"))["domain"].nunique()
                         .reindex(series.index, fill_value=0))

        evidence = _select_evidence(day, pattern, EVIDENCE_PER_SHIFT)
        if len(evidence) < EVIDENCE_PER_SHIFT:
            # Backfill from the window so a quiet publication day still gets a
            # usable source base; the date on each record stays truthful.
            extra = _select_evidence(window[window.date != row["date"]], pattern,
                                     EVIDENCE_PER_SHIFT - len(evidence) + 8)
            known = {item["domain"] for item in evidence}
            evidence += [item for item in extra if item["domain"] not in known][:EVIDENCE_PER_SHIFT - len(evidence)]

        # Days where coverage moved materially relative to the window mean --
        # these date the story without asserting an origin. Each carries its own
        # representative reports so a dated entry can say what was published
        # that day rather than only how much was.
        mean = float(series.mean()) or 1.0
        notable = []
        for date, count in series.items():
            if count < max(3, mean * 1.25):
                continue
            day_slice = window[window.date.dt.strftime("%Y-%m-%d") == date]
            notable.append({
                "date": date, "articles": int(count), "domains": int(domain_series[date]),
                "changeVsAverage": round((count - mean) / mean, 2),
                "topReports": _select_evidence(day_slice, pattern, 3),
            })
        notable = notable[-6:]

        result[slug] = {
            "slug": slug,
            "topic": topic,
            "category": category,
            "publishedDate": published,
            "articleCount": int(len(day)),
            "domainCount": int(day.domain.nunique()),
            "windowArticleCount": int(len(window)),
            "windowDomainCount": int(window.domain.nunique()),
            "windowStart": str(window_start.date()),
            "series": [{"date": date, "articles": int(count), "domains": int(domain_series[date])}
                       for date, count in series.items()],
            "notableDays": notable,
            "organizations": _rollup(day.organizations if len(day) else window.organizations, 12),
            "people": _rollup(day.persons if len(day) else window.persons, 12),
            "themes": _themes(day.themes if len(day) else window.themes, 10),
            "topDomains": [{"domain": domain, "articles": int(count)} for domain, count
                           in (day.domain if len(day) else window.domain).value_counts().head(10).items()],
            "evidence": evidence,
        }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return {
        "publishedDate": published,
        "shifts": {slug: {"evidence": len(value["evidence"]), "articles": value["articleCount"],
                          "themes": len(value["themes"]), "organizations": len(value["organizations"])}
                   for slug, value in result.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--articles", type=Path, default=DEFAULT_ARTICLES)
    parser.add_argument("--shifts", type=Path, default=DEFAULT_SHIFTS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    print(json.dumps(build(args.articles, args.shifts, args.out), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
