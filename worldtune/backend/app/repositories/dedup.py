"""Cross-source deduplication.

The same story reaches WorldTune from GDELT and Google News with different
URLs, different punctuation and a publisher suffix; the same job is posted to
RemoteOK and Adzuna with different ids. Counting those twice inflates news
volume and skill-mention counts, which are inputs to the score -- so dedup is
a correctness requirement, not tidiness.

Approach: a normalized content hash. Lowercase, strip punctuation, drop
stopwords, sort the remaining tokens, hash. Sorting the tokens makes the hash
robust to reordered headlines ("Nvidia beats estimates" vs "Estimates beaten
by Nvidia" -- the latter still differs by inflection, which this will miss;
see the limitation below).

Documented limitation: this is exact-match-after-normalization, not semantic
near-duplicate detection. Paraphrases with genuinely different wording
survive as separate rows. A shingled MinHash/LSH pass is the upgrade; it is
not warranted at prototype volume, where the dominant duplicate mode is the
identical headline syndicated across outlets.
"""
from __future__ import annotations

import hashlib
import re

_PUNCT_RE = re.compile(r"[^a-z0-9\s]+")
_WS_RE = re.compile(r"\s+")

_STOPWORDS = frozenset(
    """a an the and or of to in for on with at by from as is are was were be been
    will would its it this that has have had after before amid over under""".split()
)


def normalize_text(text: str) -> str:
    lowered = _PUNCT_RE.sub(" ", (text or "").lower())
    return _WS_RE.sub(" ", lowered).strip()


def content_hash(*parts: str) -> str:
    """Order-insensitive normalized hash over the significant tokens."""
    tokens: list[str] = []
    for part in parts:
        tokens.extend(t for t in normalize_text(part).split() if t not in _STOPWORDS)
    if not tokens:
        return ""
    joined = " ".join(sorted(set(tokens)))
    return hashlib.sha256(joined.encode()).hexdigest()[:32]


def news_hash(title: str, *, domain: str = "") -> str:
    """Deliberately excludes the domain: the point is to collapse the SAME
    headline across DIFFERENT outlets. `domain` is accepted so callers can opt
    into per-outlet hashing when they want syndication counted."""
    return content_hash(title, domain) if domain else content_hash(title)


def job_hash(title: str, company: str, location: str = "") -> str:
    """Same role at the same company in the same place is one job, whatever
    the board. Location is included because genuinely parallel openings in
    different cities are different jobs."""
    return content_hash(title, company, location)


def tech_hash(name: str, title: str = "") -> str:
    return content_hash(name, title)
