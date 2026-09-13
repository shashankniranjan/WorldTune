"""PersonaRelevance -- "does this matter to *me*?"

Three complementary mechanisms, blended, each contributing something the
others cannot:

  1. **Rules** (exact, high-precision): is this ticker on my watchlist? is
     this sector one I said I care about? is this job in my city?
  2. **Entity-graph propagation** (structured, explains itself): a signal
     about CUDA reaches a persona interested in "AI infrastructure" because
     the config file says those nodes are two hops apart.
  3. **Embedding similarity** (lexical backstop): catches persona-signal
     word overlap the taxonomy has not been taught yet.

Every sub-score is returned alongside the total, because a relevance number
with no breakdown is unauditable -- and "why am I seeing this?" is the
question this product exists to answer.

All sub-scores are in [0, 1] and all blends are convex, so the result is in
[0, 1] by construction rather than by clamping after the fact.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.entities.graph import get_entity_graph
from app.ranking.embedding import cosine_similarity, embed_terms, embed_text
from app.schemas.persona import Persona, PersonaBase
from app.skills.extraction import normalize_persona_skills

# Seniority ladder used for distance-based matching.
SENIORITY_RANK = {"junior": 1, "mid": 2, "senior": 3, "staff": 4, "principal": 5}


@dataclass
class RelevanceResult:
    score: float
    components: dict[str, float] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"score": round(self.score, 4),
                "components": {k: round(v, 4) for k, v in self.components.items()},
                "reasons": self.reasons}


def persona_text(persona: PersonaBase | Persona) -> str:
    """The persona's full text surface, used for embedding similarity."""
    return " ".join(filter(None, [
        persona.career.current_role,
        " ".join(persona.career.target_roles),
        " ".join(persona.career.skills),
        persona.career.industry,
        " ".join(persona.financial.watchlist),
        " ".join(persona.financial.sectors),
        " ".join(persona.financial.asset_classes),
        " ".join(persona.preferences.learning_topics),
        persona.location.city,
        persona.location.country,
    ]))


def persona_entity_weights(persona: PersonaBase | Persona) -> dict[str, float]:
    """Entity-graph nodes the persona cares about, with propagated weights."""
    graph = get_entity_graph()
    seeds = graph.resolve_text(
        " ".join(persona.financial.watchlist + persona.financial.sectors
                 + persona.financial.asset_classes + persona.preferences.learning_topics
                 + persona.career.skills + persona.career.target_roles)
    )
    return graph.expand(seeds)


# --- Financial relevance -----------------------------------------------------

def financial_relevance(
    persona: PersonaBase | Persona,
    *,
    symbol: str,
    asset_class: str = "",
    sector: str = "",
    signal_text: str = "",
    entities: list[str] | None = None,
) -> RelevanceResult:
    """Sub-scores per spec section 14 (financial side).

    Watchlist membership is weighted heaviest and deliberately so: an explicit
    "I hold BTC" is a stronger statement of interest than any inferred
    affinity, and a personalization product that buries the user's own stated
    watchlist under a clever model has failed at its one job.
    """
    reasons: list[str] = []
    symbol_up = (symbol or "").upper()

    watchlist = {w.upper() for w in persona.financial.watchlist}
    watchlist_hit = 1.0 if symbol_up in watchlist else 0.0
    if watchlist_hit:
        reasons.append(f"{symbol_up} is on your watchlist")

    sectors = {s.lower() for s in persona.financial.sectors}
    sector_hit = 1.0 if sector and sector.lower() in sectors else 0.0
    if sector_hit:
        reasons.append(f"{sector} is one of your tracked sectors")

    classes = {c.lower() for c in persona.financial.asset_classes}
    class_hit = 1.0 if asset_class and asset_class.lower() in classes else 0.0
    if class_hit and not watchlist_hit:
        reasons.append(f"you follow {asset_class} as an asset class")

    # Entity-graph overlap between the persona's interests and this signal.
    graph = get_entity_graph()
    persona_weights = persona_entity_weights(persona)
    signal_keys = graph.resolve_text(signal_text, symbol_up, sector,
                                     " ".join(entities or []))
    signal_weights = graph.expand(signal_keys)
    graph_overlap = _weighted_overlap(persona_weights, signal_weights)
    if graph_overlap > 0.25:
        shared = _top_shared(persona_weights, signal_weights, graph)
        if shared:
            reasons.append("connected to your interests via " + ", ".join(shared))

    embed_sim = cosine_similarity(
        embed_text(persona_text(persona)),
        embed_text(" ".join(filter(None, [signal_text, symbol_up, sector]))),
    )

    components = {
        "watchlist_membership": watchlist_hit,
        "sector_preference": sector_hit,
        "asset_class_preference": class_hit,
        "entity_graph_overlap": graph_overlap,
        "embedding_similarity": embed_sim,
    }
    score = (
        0.40 * watchlist_hit
        + 0.20 * sector_hit
        + 0.10 * class_hit
        + 0.20 * graph_overlap
        + 0.10 * embed_sim
    )
    return RelevanceResult(score=min(1.0, score), components=components, reasons=reasons)


# --- Career relevance --------------------------------------------------------

def career_relevance(
    persona: PersonaBase | Persona,
    *,
    title: str = "",
    skills: list[str] | None = None,
    location: str = "",
    remote: bool = False,
    seniority: str = "",
    signal_text: str = "",
) -> RelevanceResult:
    """Sub-scores per spec section 14 (career side): skill overlap, role
    overlap, location relevance, seniority match, plus the graph/embedding
    backstops."""
    reasons: list[str] = []

    persona_skills = set(normalize_persona_skills(persona.career.skills))
    signal_skills = set(skills or [])
    if signal_skills:
        overlap = persona_skills & signal_skills
        skill_overlap = len(overlap) / len(signal_skills)
        if overlap:
            reasons.append(f"{len(overlap)} of your skills match ({', '.join(sorted(overlap))})")
    else:
        skill_overlap = 0.0

    role_overlap = _role_overlap(persona, title)
    if role_overlap > 0.5:
        reasons.append(f"'{title}' matches one of your target roles")

    location_score = _location_relevance(persona, location, remote)
    if location_score >= 0.9:
        reasons.append(f"located in {location or 'your city'}")
    elif remote:
        reasons.append("remote-friendly")

    seniority_score = _seniority_match(persona, seniority)

    graph = get_entity_graph()
    persona_weights = persona_entity_weights(persona)
    signal_weights = graph.expand(graph.resolve_text(signal_text, title))
    graph_overlap = _weighted_overlap(persona_weights, signal_weights)

    embed_sim = cosine_similarity(
        embed_terms(persona.career.skills + persona.career.target_roles
                    + persona.preferences.learning_topics),
        embed_text(" ".join(filter(None, [title, signal_text]))),
    )

    components = {
        "skill_overlap": skill_overlap,
        "role_overlap": role_overlap,
        "location_relevance": location_score,
        "seniority_match": seniority_score,
        "entity_graph_overlap": graph_overlap,
        "embedding_similarity": embed_sim,
    }
    score = (
        0.32 * skill_overlap
        + 0.24 * role_overlap
        + 0.14 * location_score
        + 0.12 * seniority_score
        + 0.10 * graph_overlap
        + 0.08 * embed_sim
    )
    return RelevanceResult(score=min(1.0, score), components=components, reasons=reasons)


def skill_relevance(persona: PersonaBase | Persona, *, skill_id: str,
                    skill_name: str = "") -> RelevanceResult:
    """Relevance of a *skill* to the persona.

    Asymmetric on purpose: a skill the persona already has is relevant
    (it is their livelihood, and its decline is news), but a skill they lack
    that sits inside a stated learning topic is relevant *and* actionable --
    which is the whole premise of Career Pulse. Hence `learning_gap` scoring
    above `already_have`.
    """
    have = set(normalize_persona_skills(persona.career.skills))
    already_have = 1.0 if skill_id in have else 0.0

    topics = " ".join(persona.preferences.learning_topics + persona.career.target_roles)
    graph = get_entity_graph()
    topic_weights = graph.expand(graph.resolve_text(topics))
    skill_weights = graph.expand(graph.resolve_text(skill_name or skill_id))
    topical = _weighted_overlap(topic_weights, skill_weights)

    learning_gap = topical if already_have == 0.0 else 0.0

    embed_sim = cosine_similarity(
        embed_terms(persona.preferences.learning_topics + persona.career.target_roles),
        embed_text(skill_name or skill_id),
    )
    components = {
        "already_have": already_have,
        "learning_gap": learning_gap,
        "topical_overlap": topical,
        "embedding_similarity": embed_sim,
    }
    reasons = []
    if already_have:
        reasons.append(f"{skill_name or skill_id} is in your current skill set")
    if learning_gap > 0.3:
        reasons.append(f"{skill_name or skill_id} sits inside your stated learning topics")
    score = 0.35 * already_have + 0.35 * learning_gap + 0.20 * topical + 0.10 * embed_sim
    return RelevanceResult(score=min(1.0, score), components=components, reasons=reasons)


# --- helpers -----------------------------------------------------------------

def _weighted_overlap(a: dict[str, float], b: dict[str, float]) -> float:
    """Weighted Jaccard-style overlap of two entity-weight maps, in [0, 1]."""
    if not a or not b:
        return 0.0
    shared = sum(min(a[k], b[k]) for k in a.keys() & b.keys())
    total = sum(max(a.get(k, 0.0), b.get(k, 0.0)) for k in a.keys() | b.keys())
    return float(shared / total) if total else 0.0


def _top_shared(a: dict[str, float], b: dict[str, float], graph, limit: int = 2) -> list[str]:
    shared = sorted(a.keys() & b.keys(), key=lambda k: -min(a[k], b[k]))
    return [graph.label(k) for k in shared[:limit]]


def _role_overlap(persona: PersonaBase | Persona, title: str) -> float:
    """Token-level overlap of `title` against target roles and current role.

    Target roles are worth more than the current role -- the persona told us
    where they want to go, and a product about trajectory should weight the
    destination above the origin.
    """
    if not title:
        return 0.0
    title_tokens = set(title.lower().replace(",", " ").split())
    best_target = 0.0
    for role in persona.career.target_roles:
        role_tokens = set(role.lower().split())
        if role_tokens:
            best_target = max(best_target, len(title_tokens & role_tokens) / len(role_tokens))
    current_tokens = set((persona.career.current_role or "").lower().split())
    current = (len(title_tokens & current_tokens) / len(current_tokens)) if current_tokens else 0.0
    return float(min(1.0, 0.75 * best_target + 0.25 * current))


def _location_relevance(persona: PersonaBase | Persona, location: str, remote: bool) -> float:
    city = (persona.location.city or "").lower()
    country = (persona.location.country or "").lower()
    loc = (location or "").lower()
    if city and city in loc:
        return 1.0
    if remote and country and country in loc:
        return 0.85     # remote within the persona's country: no visa/timezone friction
    if remote:
        return 0.6      # remote-global: plausible but timezone-dependent
    if country and country in loc:
        return 0.55     # same country, different city: relocation required
    return 0.15


def _seniority_match(persona: PersonaBase | Persona, seniority: str) -> float:
    """1.0 at the persona's level or one step up, decaying with distance.

    One step *up* is treated as a perfect match rather than a stretch: a
    10-year Senior engineer targeting Staff roles wants to see Staff postings
    at full strength, which is precisely what the persona's target_roles say.
    """
    if not seniority:
        return 0.5
    target_ranks = [SENIORITY_RANK[s] for r in persona.career.target_roles
                    for s in SENIORITY_RANK if s in r.lower()]
    years = persona.career.years_experience
    implied = 4 if years >= 12 else 3 if years >= 7 else 2 if years >= 3 else 1
    current_ranks = [SENIORITY_RANK[s] for s in SENIORITY_RANK
                     if s in (persona.career.current_role or "").lower()]
    base = max(current_ranks) if current_ranks else implied
    candidates = set(target_ranks) | {base, base + 1}
    rank = SENIORITY_RANK.get(seniority.lower(), 2)
    distance = min(abs(rank - c) for c in candidates)
    return float(max(0.0, 1.0 - 0.35 * distance))
