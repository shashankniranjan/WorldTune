"""Seniority and role-family classification for job titles.

Rules, not a model. The vocabulary of engineering job titles is small and
adversarially inconsistent ("Senior Staff", "SDE III", "Lead Engineer II"),
which is exactly the regime where an ordered rule list beats a classifier and
stays explainable. Applied to the *title* only -- descriptions routinely
mention other seniorities ("you will mentor junior engineers").
"""
from __future__ import annotations

import re

# Ordered most-senior-first; the first match wins, so "Senior Staff Engineer"
# resolves to staff rather than senior.
_SENIORITY_RULES: tuple[tuple[str, str], ...] = (
    ("principal", r"\b(principal|distinguished|fellow)\b"),
    ("staff", r"\b(staff|architect|lead|l[56]|sde\s*(iv|4))\b"),
    ("senior", r"\b(senior|sr\.?|sde\s*(iii|3)|l4)\b"),
    ("junior", r"\b(junior|jr\.?|associate|graduate|intern|entry[- ]level)\b"),
)

_ROLE_FAMILY_RULES: tuple[tuple[str, str], ...] = (
    ("ai-ml", r"\b(ml|machine learning|ai|llm|genai|research (scientist|engineer)|mlops)\b"),
    ("platform", r"\b(platform|infrastructure|infra|devops|sre|site reliability)\b"),
    ("data-engineering", r"\b(data engineer|data engineering|analytics engineer|etl|pipeline|"
                        r"data platform|big data|streaming)\b"),
    ("analytics", r"\b(data analyst|business intelligence|bi |analytics)\b"),
    ("software", r"\b(software|backend|full[- ]stack|developer)\b"),
)


def classify_seniority(title: str) -> str:
    lowered = (title or "").lower()
    for label, pattern in _SENIORITY_RULES:
        if re.search(pattern, lowered):
            return label
    return "mid"


def classify_role_family(title: str, description: str = "") -> str:
    """Family from the title; the description is a tiebreak only.

    Ordered so that "Senior ML Platform Engineer" lands in ai-ml (the
    discipline) rather than platform (the surface), which is how the demo
    persona's target roles are phrased.
    """
    lowered = (title or "").lower()
    for label, pattern in _ROLE_FAMILY_RULES:
        if re.search(pattern, lowered):
            return label
    lowered_desc = (description or "").lower()[:600]
    for label, pattern in _ROLE_FAMILY_RULES:
        if re.search(pattern, lowered_desc):
            return label
    return "other"


def is_remote(title: str, location: str, tags: list[str] | None = None) -> bool:
    blob = " ".join([title or "", location or ""] + list(tags or [])).lower()
    return bool(re.search(r"\b(remote|anywhere|work from home|distributed)\b", blob))
