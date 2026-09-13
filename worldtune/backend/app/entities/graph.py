"""Entity graph: load config/entity_graph.yaml, match text to nodes, and
propagate relevance along edges (spec section 28).

Two jobs:

  1. `resolve_text()` -- alias matching over free text. Longest-alias-first,
     word-boundary anchored, so "ml" does not fire inside "html" and
     "apache iceberg" wins over a bare "iceberg".
  2. `expand()` -- breadth-first walk from a set of matched nodes, multiplying
     by `decay` per hop up to `max_hops`. This is the mechanism by which a
     persona interested in "AI infrastructure" scores an NVIDIA headline
     above zero without anyone hardcoding that pair.

Deliberately a config file and an adjacency dict, not a graph database: the
taxonomy is a few hundred nodes, and the honest cost of Neo4j here would be
operational, not analytical.
"""
from __future__ import annotations

import functools
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import yaml

# worldtune/backend/app/entities/graph.py -> worldtune/config/entity_graph.yaml
# `WORLDTUNE_ENTITY_GRAPH` overrides it, so a deployment that relocates the
# config (or wants to A/B a different taxonomy) needs no code change.
DEFAULT_CONFIG_PATH = Path(
    os.environ.get("WORLDTUNE_ENTITY_GRAPH")
    or Path(__file__).resolve().parents[3] / "config" / "entity_graph.yaml"
)


@dataclass(frozen=True)
class EntityNode:
    key: str
    label: str
    type: str
    aliases: tuple[str, ...] = ()
    tickers: tuple[str, ...] = ()
    edges: tuple[str, ...] = ()


@dataclass
class EntityGraph:
    nodes: dict[str, EntityNode] = field(default_factory=dict)
    decay: float = 0.6
    max_hops: int = 3
    _alias_index: list[tuple[str, str]] = field(default_factory=list, repr=False)

    # -- construction --------------------------------------------------------
    @classmethod
    def from_config(cls, path: Path | str | None = None) -> "EntityGraph":
        cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
        raw = yaml.safe_load(cfg_path.read_text()) or {}
        nodes: dict[str, EntityNode] = {}
        for key, spec in (raw.get("nodes") or {}).items():
            spec = spec or {}
            nodes[key] = EntityNode(
                key=key,
                label=spec.get("label", key),
                type=spec.get("type", "topic"),
                aliases=tuple(a.lower() for a in spec.get("aliases", []) or []),
                tickers=tuple(spec.get("tickers", []) or []),
                edges=tuple(spec.get("edges", []) or []),
            )
        graph = cls(nodes=nodes, decay=float(raw.get("decay", 0.6)),
                    max_hops=int(raw.get("max_hops", 3)))
        graph._build_alias_index()
        return graph

    def _build_alias_index(self) -> None:
        pairs: list[tuple[str, str]] = []
        for node in self.nodes.values():
            seen = set(node.aliases) | {node.label.lower()} | {t.lower() for t in node.tickers}
            for alias in seen:
                if alias:
                    pairs.append((alias, node.key))
        # Longest alias first so multi-word phrases beat their substrings.
        pairs.sort(key=lambda p: len(p[0]), reverse=True)
        self._alias_index = pairs

    # -- lookup --------------------------------------------------------------
    def resolve_text(self, *texts: str) -> list[str]:
        """Return node keys whose alias appears in any of `texts`."""
        blob = " ".join(t for t in texts if t).lower()
        if not blob:
            return []
        found: list[str] = []
        for alias, key in self._alias_index:
            if key in found:
                continue
            pattern = r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])"
            if re.search(pattern, blob):
                found.append(key)
        return found

    def expand(self, keys: Iterable[str], *, decay: float | None = None,
               max_hops: int | None = None) -> dict[str, float]:
        """BFS from `keys`, returning {node_key: relevance_weight in (0, 1]}.

        A node reached by several paths keeps its strongest weight.
        """
        decay = self.decay if decay is None else decay
        max_hops = self.max_hops if max_hops is None else max_hops
        weights: dict[str, float] = {}
        frontier: list[tuple[str, float, int]] = [
            (k, 1.0, 0) for k in keys if k in self.nodes
        ]
        while frontier:
            key, weight, hop = frontier.pop(0)
            if weights.get(key, 0.0) >= weight:
                continue
            weights[key] = weight
            if hop >= max_hops:
                continue
            for nxt in self.nodes[key].edges:
                if nxt in self.nodes:
                    frontier.append((nxt, weight * decay, hop + 1))
        return weights

    def tickers_for(self, keys: Iterable[str]) -> list[str]:
        out: list[str] = []
        for k in keys:
            node = self.nodes.get(k)
            if node:
                out.extend(t for t in node.tickers if t not in out)
        return out

    def sectors_for(self, keys: Iterable[str]) -> list[str]:
        """Sector-typed nodes reachable from `keys` (used to tag news)."""
        out: list[str] = []
        for k, _w in sorted(self.expand(keys).items(), key=lambda kv: -kv[1]):
            node = self.nodes.get(k)
            if node and node.type == "sector" and node.label not in out:
                out.append(node.label)
        return out

    def label(self, key: str) -> str:
        node = self.nodes.get(key)
        return node.label if node else key


@functools.lru_cache(maxsize=1)
def get_entity_graph() -> EntityGraph:
    """Process-wide singleton. Config is small and read-only at runtime."""
    return EntityGraph.from_config()
