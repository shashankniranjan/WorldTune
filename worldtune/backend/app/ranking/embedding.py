"""Deterministic text embedding (hashing trick).

An honest simplification, stated plainly: this is a bag-of-words hashing
vector with sublinear term weighting, L2-normalized -- not a semantic
embedding model. It cannot tell you that "lakehouse" and "Iceberg" are
related. What it *can* do is run offline with no model download, no network
call and no GPU, produce the same vector every time, and be checked by hand.

Semantic relatedness is not lost, it is just handled elsewhere and more
transparently: the entity graph (config/entity_graph.yaml) supplies the
"lakehouse -> Iceberg" edges explicitly, and the rules in
`app.ranking.relevance` supply the structured overlaps. Embedding similarity
contributes a modest slice of PersonaRelevance as a lexical backstop for text
the graph does not cover.

Upgrade path: swap `embed_text` for a sentence-transformer call and store the
vectors in the pgvector column described in app/models/base.py. Nothing else
changes -- callers only ever see `cosine_similarity`.
"""
from __future__ import annotations

import hashlib
import math
import re

EMBEDDING_DIM = 128

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+#.\-]*")

# High-frequency words that would otherwise dominate every vector.
_STOPWORDS = frozenset(
    """a an the and or of to in for on with at by from as is are was were be been
    will would can could should this that these those it its our your their we you
    they he she i not no but if then than so such into over under out up down more
    most other some any all each new role job work team using use used join""".split()
)


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall((text or "").lower())
            if t not in _STOPWORDS and len(t) > 1]


def _bucket(token: str, dim: int) -> int:
    return int(hashlib.sha256(token.encode()).hexdigest()[:8], 16) % dim


def embed_text(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    """L2-normalized hashed bag-of-words with 1+log(tf) term weighting.

    Sublinear tf matters here: a job description that says "Spark" nine times
    is not nine times more about Spark than one that says it once, and raw
    counts would let a verbose posting outrank a relevant one.
    """
    vec = [0.0] * dim
    counts: dict[str, int] = {}
    for token in tokenize(text):
        counts[token] = counts.get(token, 0) + 1
    for token, tf in counts.items():
        vec[_bucket(token, dim)] += 1.0 + math.log(tf)
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def embed_terms(terms: list[str], dim: int = EMBEDDING_DIM) -> list[float]:
    """Embed a list of short phrases (skills, sectors, roles) as one vector."""
    return embed_text(" ".join(terms or []), dim=dim)


def cosine_similarity(a: list[float] | None, b: list[float] | None) -> float:
    """Cosine similarity, clamped to [0, 1] (both inputs are non-negative)."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    return float(max(0.0, min(1.0, dot)))
