"""Declarative structure for World Shift domain knowledge.

A pack answers the questions a reader has about a shift that no amount of
article counting can answer: what the thing is, what mechanism connects it to
money or to engineering, who the recurring actors are, and what observation
would change the interpretation.

A pack contains no facts about the current news cycle. Everything time-bound --
which publishers are reporting, which entities appear, how attention moved --
comes from the source artifact and is joined in by the composer. That split is
what keeps one composer able to serve every shift.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Direction = Literal["positive", "negative", "mixed", "uncertain", "up", "down", "neutral"]
Ring = Literal["direct", "supply_chain", "second_order"]
Horizon = Literal["immediate", "7d", "30d", "90d", "long_term"]


@dataclass(frozen=True)
class Claim:
    """One analytical statement with its transmission mechanism attached."""

    title: str
    summary: str
    mechanism: str
    horizon: Horizon = "30d"
    direction: Direction = "uncertain"
    magnitude: str = "medium"
    confidence: str = "medium"
    invalidators: tuple[str, ...] = ()


@dataclass(frozen=True)
class Exposure:
    """A named organisation whose operations may be sensitive to the shift.

    Deliberately reasoned rather than observed: the corpus establishes that the
    shift is being reported, not that any particular company is affected. The
    reasoning chain is the product -- it is what lets a reader disagree.
    """

    key: str
    name: str
    ticker: str | None
    direction: Literal["positive", "negative", "mixed"]
    ring: Ring
    mechanism: str
    reasoning: tuple[str, ...]
    countries: tuple[str, ...]
    horizons: tuple[Literal["near_term", "long_term"], ...]
    verify: str
    opportunity_type: str
    confidence: str = "medium"


@dataclass(frozen=True)
class LensGroup:
    """A grouping for the persona "Your lens" tab."""

    title: str
    entity_type: str
    items: tuple[tuple[str, Direction, str], ...]  # (name, direction, summary)


@dataclass(frozen=True)
class ScenarioSpec:
    label: Literal["base", "upside", "downside"]
    title: str
    summary: str
    horizon: Literal["7d", "30d", "90d"]
    triggers: tuple[str, ...]
    indicators: tuple[str, ...]
    invalidators: tuple[str, ...]
    implications: tuple[str, ...]
    confidence: str = "medium"


@dataclass(frozen=True)
class PersonaPack:
    """Everything one persona needs. The two personas share no prose."""

    # Section labels. These drive the page headings, so a heading can never
    # describe a different shift than the content beneath it.
    kicker: str
    headline: str
    summary: str
    lens_title: str
    lens_blurb: str
    exposure_headline: str
    exposure_blurb: str
    direct: tuple[Claim, ...]
    chain: tuple[Claim, ...]
    second_order: tuple[Claim, ...]
    opportunities: tuple[Claim, ...]
    risks: tuple[Claim, ...]
    watch: tuple[Claim, ...]
    exposures: tuple[Exposure, ...]
    lens_groups: tuple[LensGroup, ...]
    scenarios: tuple[ScenarioSpec, ...]
    scenario_framing: str
    path_steps: tuple[str, ...]
    path_title: str
    path_explanation: str


@dataclass(frozen=True)
class Downstream:
    """A shift-to-shift or shift-to-system consequence with a mechanism."""

    title: str
    relationship: str
    explanation: str
    mechanism: str
    confidence: str = "medium"
    shift_slug: str | None = None
    indicators: tuple[str, ...] = ()


@dataclass(frozen=True)
class ActorSpec:
    """A recurring institution, with the role it plays in this shift."""

    name: str
    role: str
    position: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class Hero:
    url: str
    caption: str
    credit: str


@dataclass(frozen=True)
class KnowledgePack:
    slug: str
    subject: str
    what_it_is: str
    why_it_matters: str
    system_framing: str
    timeline_kicker: str
    timeline_heading: str
    hero: Hero | None
    causes: tuple[str, ...]
    drivers: tuple[str, ...]
    uncertainty: tuple[str, ...]
    indicators: tuple[str, ...]
    actors: tuple[ActorSpec, ...]
    downstream: tuple[Downstream, ...]
    themes: tuple[str, ...]
    finance: PersonaPack
    tech: PersonaPack
    upstream: tuple[str, ...] = field(default=())

    def persona(self, persona: str) -> PersonaPack:
        return self.finance if persona == "finance" else self.tech
