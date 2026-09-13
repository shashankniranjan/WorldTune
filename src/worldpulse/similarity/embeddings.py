"""Lightweight deterministic embedding for WorldEvent records.

Uses a hashing-trick bag-of-words vector over event_type + entities +
countries + affected_channels, L2-normalized. This requires no network
access or model download, so it works fully offline in tests -- a
deliberate simplification vs. a real semantic embedding model, documented
in docs/LLD.md.
"""
from __future__ import annotations

import hashlib
import math

from worldpulse.events.schemas import WorldEvent

EMBEDDING_DIM = 128


def _token_hash_index(token: str, dim: int = EMBEDDING_DIM) -> int:
    digest = hashlib.sha256(token.lower().encode()).hexdigest()
    return int(digest[:8], 16) % dim


def _tokens_for_event(event: WorldEvent) -> list[str]:
    tokens: list[str] = []
    event_type = event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type)
    tokens.append(f"type:{event_type}")
    tokens.append(f"subtype:{event.event_subtype}")
    tokens.extend(f"country:{c}" for c in event.countries)
    tokens.extend(f"entity:{e}" for e in event.entities)
    tokens.extend(f"channel:{c}" for c in event.affected_channels)
    return tokens


def embed_event(event: WorldEvent, dim: int = EMBEDDING_DIM) -> list[float]:
    """Hashing-trick term-frequency vector, L2-normalized."""
    vec = [0.0] * dim
    for token in _tokens_for_event(event):
        idx = _token_hash_index(token, dim)
        vec[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
