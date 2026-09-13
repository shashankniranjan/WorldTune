"""Deterministic skill extraction from job text (spec section 9).

No LLM. Extraction is keyword/phrase matching with word-boundary anchoring,
because the counts it produces are the denominator of every Career Pulse
metric -- they must be reproducible run to run and explainable to a user
("Iceberg appeared in 14 of 52 postings"). An LLM would make the same numbers
non-deterministic for no accuracy gain on a closed vocabulary.

Matching rules that actually matter in practice:
  * word-boundary anchored, so "SQL" does not match "NoSQLish" and "ML"
    does not match "HTML";
  * longest phrase first, so "Delta Lake" is not double-counted as "Delta"
    plus a stray "Lake";
  * once a span is consumed by a longer alias it cannot be re-matched by a
    shorter one.
"""
from __future__ import annotations

import re
from collections import Counter

from app.skills.taxonomy import SKILL_LOOKUP, SKILLS_BY_ID, Skill

# Aliases sorted longest-first; each compiled once at import.
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?<![a-z0-9+#.])" + re.escape(alias) + r"(?![a-z0-9+#])", re.IGNORECASE), skill_id)
    for alias, skill_id in sorted(SKILL_LOOKUP.items(), key=lambda kv: -len(kv[0]))
]


def extract_skills(text: str) -> Counter:
    """Return Counter{skill_id: mention_count} for a block of job text."""
    if not text:
        return Counter()
    lowered = text.lower()
    consumed = [False] * len(lowered)
    counts: Counter = Counter()
    for pattern, skill_id in _PATTERNS:
        for match in pattern.finditer(lowered):
            start, end = match.span()
            if any(consumed[start:end]):
                continue  # already claimed by a longer alias
            for i in range(start, end):
                consumed[i] = True
            counts[skill_id] += 1
    return counts


def extract_skill_ids(text: str) -> list[str]:
    """Distinct skill ids mentioned, most-mentioned first."""
    return [sid for sid, _ in extract_skills(text).most_common()]


def normalize_persona_skills(skills: list[str]) -> list[str]:
    """Map a persona's free-text skill list onto canonical skill ids.

    Unknown entries are dropped from the *canonical* view but the raw strings
    stay on the persona -- we never silently rewrite what the user typed.
    """
    out: list[str] = []
    for raw in skills:
        sid = SKILL_LOOKUP.get(raw.strip().lower())
        if sid is None:
            # Fall back to a full-text scan, which catches "Google BigQuery".
            found = extract_skill_ids(raw)
            sid = found[0] if found else None
        if sid and sid not in out:
            out.append(sid)
    return out


def skill(skill_id: str) -> Skill | None:
    return SKILLS_BY_ID.get(skill_id)
