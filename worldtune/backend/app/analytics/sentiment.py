"""Lexicon sentiment scorer for headlines.

Deliberately a small, finance/tech-tuned lexicon rather than a transformer:
it needs no model download, runs offline, is deterministic, and its output is
explainable ("scored -0.4: 'plunge', 'downgrade'"). Providers that publish
their own tone (GDELT) use theirs instead; this is the fallback.

Documented simplification: no negation handling, no sarcasm, no aspect
targeting. Sentiment feeds the score as one of thirteen inputs and is never
the sole driver of a recommendation.
"""
from __future__ import annotations

import re

POSITIVE = {
    "surge": 1.0, "surges": 1.0, "soar": 1.0, "soars": 1.0, "rally": 0.9, "rallies": 0.9,
    "jump": 0.8, "jumps": 0.8, "gain": 0.6, "gains": 0.6, "rise": 0.5, "rises": 0.5,
    "beat": 0.8, "beats": 0.8, "record": 0.7, "upgrade": 0.9, "upgraded": 0.9,
    "breakthrough": 0.9, "growth": 0.6, "strong": 0.6, "outperform": 0.8,
    "adoption": 0.5, "expands": 0.5, "expansion": 0.5, "hiring": 0.6, "funding": 0.5,
    "profit": 0.6, "profits": 0.6, "bullish": 1.0, "approval": 0.7, "approved": 0.7,
}
NEGATIVE = {
    "plunge": -1.0, "plunges": -1.0, "crash": -1.0, "crashes": -1.0, "slump": -0.9,
    "tumble": -0.9, "tumbles": -0.9, "fall": -0.5, "falls": -0.5, "drop": -0.6, "drops": -0.6,
    "miss": -0.8, "misses": -0.8, "downgrade": -0.9, "downgraded": -0.9, "cut": -0.5,
    "cuts": -0.5, "layoff": -1.0, "layoffs": -1.0, "loss": -0.7, "losses": -0.7,
    "weak": -0.6, "bearish": -1.0, "probe": -0.6, "lawsuit": -0.7, "ban": -0.8,
    "outage": -0.7, "breach": -0.8, "selloff": -0.9, "warning": -0.6, "hiring freeze": -0.9,
}

_TOKEN_RE = re.compile(r"[a-z][a-z\-']+")


def score_sentiment(text: str) -> float:
    """Return sentiment in [-1, 1]; 0.0 when no lexicon term is present."""
    if not text:
        return 0.0
    lowered = text.lower()
    total = 0.0
    hits = 0
    for phrase, weight in NEGATIVE.items():
        if " " in phrase and phrase in lowered:
            total += weight
            hits += 1
    tokens = _TOKEN_RE.findall(lowered)
    for token in tokens:
        if token in POSITIVE:
            total += POSITIVE[token]
            hits += 1
        elif token in NEGATIVE:
            total += NEGATIVE[token]
            hits += 1
    if hits == 0:
        return 0.0
    return max(-1.0, min(1.0, total / max(1, hits)))


def explain_sentiment(text: str) -> list[str]:
    """The lexicon terms that fired -- used in evidence strings."""
    lowered = (text or "").lower()
    terms = [t for t in _TOKEN_RE.findall(lowered) if t in POSITIVE or t in NEGATIVE]
    terms += [p for p in NEGATIVE if " " in p and p in lowered]
    return sorted(set(terms))
