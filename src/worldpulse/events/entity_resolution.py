"""Lightweight entity/country name normalization.

Real-world feeds spell the same entity multiple ways ("US", "USA",
"United States"). This module provides a small deterministic alias table
plus a normalize() helper used before dedup/similarity so near-duplicate
entity names collapse to a canonical form.
"""
from __future__ import annotations

_ALIASES: dict[str, str] = {
    "us": "USA",
    "u.s.": "USA",
    "united states": "USA",
    "united states of america": "USA",
    "russian federation": "Russia",
    "prc": "China",
    "people's republic of china": "China",
    "rok": "South Korea",
    "dprk": "North Korea",
}


def normalize_entity(name: str) -> str:
    key = name.strip().lower()
    return _ALIASES.get(key, name.strip())


def normalize_entities(names: list[str]) -> list[str]:
    seen: list[str] = []
    for n in names:
        canon = normalize_entity(n)
        if canon not in seen:
            seen.append(canon)
    return seen
