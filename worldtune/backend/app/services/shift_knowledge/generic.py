"""Fallback knowledge for a shift that has no dedicated pack yet.

A detector can emit a topic before anyone has written domain knowledge for it.
Rather than falling back to a near-empty page, the generic pack derives a
category-shaped interpretation: honest about being generic, still specific
enough to give the reader a mechanism and something to verify.

Every string here is parameterised on the topic and category, so no wording
from one shift can appear on another.
"""
from __future__ import annotations

from .base import ActorSpec, Claim, Downstream, Hero, KnowledgePack, LensGroup, PersonaPack, ScenarioSpec

# Category framings. These describe how a domain generally transmits, which is
# defensible without knowing the specific topic.
CATEGORY_FRAMING: dict[str, dict[str, str]] = {
    "technology": {
        "noun": "technology capability and adoption",
        "finance": "technology spending decisions, competitive position and the cost of building or buying capability",
        "tech": "which technical problems become worth solving and which capabilities become scarce",
        "hero": "https://upload.wikimedia.org/wikipedia/commons/2/26/Datove_centrum_TCP.jpg",
        "hero_caption": "Computing infrastructure. Technology shifts usually reach people through what systems can do and what they cost to run.",
    },
    "macro_policy": {
        "noun": "economic policy and price conditions",
        "finance": "discount rates, currency effects and the cost of capital",
        "tech": "what gets funded, what gets cut and which work survives a budget review",
        "hero": "https://upload.wikimedia.org/wikipedia/commons/8/89/Eccles_Building_%2826088200676%29.jpg",
        "hero_caption": "A central-bank building. Policy decisions set the reference price for borrowing across the economy.",
    },
    "geopolitics": {
        "noun": "state action and international security",
        "finance": "risk premia, commodity and trade flows, and country exposure",
        "tech": "supply availability, deployment eligibility and sovereign capability requirements",
        "hero": "https://upload.wikimedia.org/wikipedia/commons/9/91/UN_Headquarters_2.jpg",
        "hero_caption": "International institutions. State action reaches markets and systems through trade, energy and rules rather than directly.",
    },
    "crypto": {
        "noun": "digital assets and their legal treatment",
        "finance": "who is permitted to participate and what compliance costs them",
        "tech": "what a compliant system has to prove and who can build it",
        "hero": "https://upload.wikimedia.org/wikipedia/commons/d/d2/Bitcoin_on_Laptop_Keyboard.jpg",
        "hero_caption": "Digital assets. The consequential questions are about classification, custody and reserves.",
    },
    "india": {
        "noun": "Indian policy and digital infrastructure",
        "finance": "domestic market structure, regulated pricing and credit formation",
        "tech": "building on shared public infrastructure and proving compliance on it",
        "hero": "https://upload.wikimedia.org/wikipedia/commons/a/a7/Delhi_India_Government.jpg",
        "hero_caption": "Government offices in New Delhi. Indian digital systems are operated as public infrastructure.",
    },
    "metals": {
        "noun": "metals, commodities and store-of-value demand",
        "finance": "real yields, currency reserves and input costs for industry",
        "tech": "materials availability for manufacturing and electronics",
        "hero": "https://upload.wikimedia.org/wikipedia/commons/c/c6/Gold_bullion_2.jpg",
        "hero_caption": "Bullion. Metals sit between industrial input cost and store-of-value demand.",
    },
}

DEFAULT_FRAMING = {
    "noun": "developments in this domain",
    "finance": "risk, cost and exposure across affected sectors",
    "tech": "which technical problems become worth solving",
    "hero": "https://upload.wikimedia.org/wikipedia/commons/9/91/UN_Headquarters_2.jpg",
    "hero_caption": "International institutions and the systems that connect them.",
}


def _persona(topic: str, category: str, persona: str, framing: dict[str, str]) -> PersonaPack:
    finance = persona == "finance"
    lens = framing["finance"] if finance else framing["tech"]
    return PersonaPack(
        kicker="Finance & investing perspective" if finance else "Tech & career perspective",
        headline=(f"Read {topic} through {lens}"),
        summary=(
            f"No dedicated analysis has been written for {topic} yet, so this reading is derived from "
            f"how {framing['noun']} generally transmits rather than from anything specific to this "
            f"development. The source records below are real and dated; the interpretation is a "
            f"starting point for your own reading, not a substitute for it."
        ),
        lens_title=(f"Where {topic} could reach money and markets" if finance
                    else f"Where {topic} could reach technology and work"),
        lens_blurb=(
            "These are general transmission paths for this domain. They are not claims that this "
            "particular development has had any of these effects."
        ),
        exposure_headline=(f"Sectors that would be first affected if {topic} develops further" if finance
                           else f"Technical areas that would be first affected if {topic} develops further"),
        exposure_blurb=(
            "No company-level analysis has been derived for this shift. Naming specific companies "
            "without a defensible transmission path would be invention, not analysis."
        ),
        direct=(
            Claim(
                f"What would have to be true for {topic} to matter here",
                (f"Attention to {topic} shows the subject is salient. For it to reach "
                 f"{'markets' if finance else 'engineering work'}, there has to be a decision, a "
                 f"measured change or a rule that alters behaviour — and the source records below do "
                 f"not yet establish one."),
                (f"reported development → {'decision or measured market change' if finance else 'change in what teams must build or can obtain'} "
                 f"→ observable effect"),
                "30d", "uncertain", "medium", "low",
                ("No official decision, measured change or rule follows the reporting",),
            ),
        ),
        chain=(
            Claim(
                f"How {framing['noun']} usually transmits",
                (f"Developments in this domain typically reach people through {lens}. That is the path "
                 f"to watch for {topic}, and each step in it is observable independently of coverage."),
                f"{framing['noun']} → {lens} → observable effect on prices, costs or capability",
                "90d", "uncertain", "medium", "low",
                ("The proposed transmission path produces no observable change",),
            ),
        ),
        second_order=(
            Claim(
                "What a wider effect would look like",
                (f"A development becomes broadly consequential when it changes behaviour in sectors "
                 f"that are not themselves part of {topic}. Until that appears in "
                 f"{'reported costs, prices or capital decisions' if finance else 'what teams build, buy or hire for'}, "
                 f"treat the significance as unestablished."),
                "domain development → behaviour change outside the domain → broader consequence",
                "90d", "uncertain", "low", "low",
                ("No change in behaviour outside the immediate domain",),
            ),
        ),
        opportunities=(),
        risks=(
            Claim(
                "Attention is not the same as change",
                (f"Coverage of {topic} can rise because of syndication, a single widely repeated story "
                 f"or editorial interest, without anything in the world having changed. This page "
                 f"reports the attention; it does not confirm the change."),
                "coverage intensity → apparent significance → conclusion the evidence does not support",
                "7d", "negative", "medium", "high",
            ),
            Claim(
                "No domain analysis has been written for this shift",
                (f"Unlike shifts with dedicated analysis, {topic} has no worked transmission model, "
                 f"named actors or verified exposure paths here. Prefer the source records to this "
                 f"summary."),
                "absent domain knowledge → generic interpretation → limited analytical value",
                "30d", "negative", "medium", "high",
            ),
        ),
        watch=(
            Claim(
                "What would make this worth revisiting",
                (f"An official decision, a measured change in "
                 f"{'prices, volumes or company disclosures' if finance else 'availability, requirements or published specifications'}, "
                 f"or independent corroboration from a second unrelated publisher."),
                "official action or measured change confirms or rejects the significance",
                "30d", "uncertain", "medium", "medium",
            ),
        ),
        exposures=(),
        lens_groups=(
            LensGroup(
                f"General transmission paths in {category.replace('_', ' ')}",
                "transmission_path",
                (
                    ("Policy and official decisions", "uncertain",
                     "Rules and decisions change behaviour directly and are published, dated and verifiable."),
                    ("Prices, costs and availability" if finance else "Availability, requirements and specifications", "uncertain",
                     "Measured changes here are the first observable evidence that something real has shifted."),
                    ("Behaviour outside the domain", "uncertain",
                     "The test of whether a development matters broadly is whether unrelated sectors change what they do."),
                ),
            ),
        ),
        scenarios=(
            ScenarioSpec("base", "Attention continues without a confirmed change",
                         f"Coverage of {topic} persists at a similar level and no official decision or measured change follows.",
                         "30d", ("Coverage continues", "No official action"),
                         ("Official decisions", "Measured domain data", "Independent corroboration"),
                         ("An official decision or measured change is confirmed",),
                         ("The shift stays informational", "No basis for acting on it"), "medium"),
            ScenarioSpec("upside", "Independent evidence establishes what changed",
                         f"Official action or measured data clarifies what has actually happened with {topic}, making it possible to reason about consequences.",
                         "90d", ("Official decision published", "Measured data released"),
                         ("Official publications", "Measured domain indicators"),
                         ("No confirming evidence appears",),
                         ("The shift becomes analysable", "A specific transmission path can be identified"), "medium"),
            ScenarioSpec("downside", "The reporting proves to be attention without substance",
                         f"No decision, measurement or corroboration follows, and coverage of {topic} declines without anything having changed.",
                         "30d", ("Coverage declines", "No corroborating evidence"),
                         ("Coverage volume", "Absence of official action"),
                         ("Corroborating evidence appears",),
                         ("The signal was media attention rather than change",), "medium"),
        ),
        scenario_framing=(
            "Conditional scenarios derived from general domain behaviour rather than from analysis "
            "specific to this shift. These are not forecasts and not advice."
        ),
        path_title=(f"How {topic} could reach a portfolio" if finance else f"How {topic} could reach your work"),
        path_steps=(topic, "official decision or measured change",
                    "prices, costs and exposure" if finance else "availability, requirements and skills",
                    "observable effect"),
        path_explanation=(
            f"This path is a hypothesis about how {topic} might become relevant, not a description of "
            f"something that has happened."
        ),
    )


def generic_pack(topic: str, category: str) -> KnowledgePack:
    framing = CATEGORY_FRAMING.get(category, DEFAULT_FRAMING)
    slug = topic.lower().replace(" ", "-")
    return KnowledgePack(
        slug=slug,
        subject=f"{topic}, within {framing['noun']}",
        what_it_is=(
            f"{topic} is currently being reported across multiple independent publishers in the "
            f"{category.replace('_', ' ')} domain. WorldTune has not yet built dedicated analysis for "
            f"this subject, so what follows sets out the reporting itself and how this domain generally "
            f"transmits, rather than asserting a specific interpretation."
        ),
        why_it_matters=(
            f"Developments in {framing['noun']} usually matter through {framing['finance']} and through "
            f"{framing['tech']}. Whether {topic} does is a question the source records below can help "
            f"answer and this summary cannot."
        ),
        system_framing=(
            f"Treat {topic} as a candidate rather than a conclusion: read the sources, identify whether "
            f"an actual decision or measured change occurred, and only then consider consequences."
        ),
        timeline_kicker="How the reporting developed",
        timeline_heading=f"Dated coverage of {topic}",
        hero=Hero(url=framing["hero"], caption=framing["hero_caption"], credit="Wikimedia Commons"),
        causes=(
            f"The source records below are what caused {topic} to register as a shift. They show what "
            f"is being reported; they do not establish why the underlying situation changed.",
        ),
        drivers=(
            f"What is being reported about {topic}, and by how many independent publishers.",
            "Whether any official decision or measured change accompanies the reporting.",
            "Whether the coverage is independent reporting or the same story carried by many outlets.",
        ),
        uncertainty=(
            "Coverage intensity can rise without any underlying change, particularly when one story is "
            "widely syndicated.",
            f"No dedicated domain analysis exists for {topic} here, so this interpretation is generic "
            f"by construction.",
            "The absence of a worked transmission model is a limitation of this page, not evidence "
            "that the subject is unimportant.",
        ),
        indicators=(
            "Official publications and decisions in this domain",
            "Measured data from the relevant sector",
            "Independent corroboration by unrelated publishers",
            "Whether coverage persists beyond a single news cycle",
        ),
        actors=(),
        downstream=(
            Downstream(
                title=f"Other developments in {category.replace('_', ' ')}",
                relationship="shares a domain with",
                explanation=(
                    f"Shifts in the same domain frequently share drivers and audiences. That makes them "
                    f"worth reading together, but it is an association rather than a causal link."
                ),
                mechanism="shared domain and drivers → correlated attention → association, not causation",
                confidence="low",
                indicators=("shared entities across shifts", "shared publishers", "temporal ordering"),
            ),
        ),
        themes=(category.replace("_", " "), "developing coverage", "unverified significance"),
        finance=_persona(topic, category, "finance", framing),
        tech=_persona(topic, category, "tech", framing),
    )
