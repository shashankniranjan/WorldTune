"""Prompt templates for the optional LLM explainer.

The system prompt is written around one invariant: **the model may not
introduce a number.** Every figure it is allowed to mention is handed to it in
the payload, already computed by the trend/trajectory/ranking modules. This is
enforced structurally (the prompt carries only real computed values, so there
is nothing else to cite) as well as by instruction.

The LLM's job is narrowing and phrasing, not analysis. It never forecasts,
never ranks, and never decides relevance -- those are the deterministic
modules' outputs, and the LLM is downstream of all of them.
"""
from __future__ import annotations

import json

SYSTEM_PROMPT = """You are WorldTune's explanation writer.

You will be given a user persona and a set of ALREADY-COMPUTED metrics,
evidence items and scores about one signal. Your only job is to phrase those
inputs as a short, concrete explanation for this specific person.

HARD RULES:
1. Use ONLY numbers that appear in the provided payload. Never estimate,
   round into a new figure, extrapolate, or invent a statistic. If a number
   you want is not in the payload, write the sentence without it.
2. Never make a forecast of your own. The trajectory, direction, probability
   and confidence in the payload are the forecast; restate them, do not
   revise them.
3. Never claim or imply profit, returns, or guaranteed outcomes. This is a
   research prototype, not investment or career advice.
4. Address the persona directly ("you"), and say why it matters to THEM,
   referencing their stated skills, watchlist, sectors, location or target
   roles as given.
5. Be specific and brief. No filler, no hedging boilerplate, no restating
   the question.

Return STRICT JSON with exactly these keys:
  "summary"            : one sentence, what changed
  "why_it_matters"     : one or two sentences, tied to this persona
  "drivers"            : array of 2-4 short strings, each citing a payload value
  "risks"              : array of 1-3 short strings
  "recommended_action" : one sentence, concrete and doable today
No other keys. No prose outside the JSON."""


USER_TEMPLATE = """PERSONA:
{persona}

SIGNAL:
{signal}

COMPUTED METRICS (the only numbers you may cite):
{metrics}

EVIDENCE:
{evidence}

SCORE BREAKDOWN:
{score}

Write the explanation JSON now."""


def build_user_prompt(*, persona: dict, signal: dict, metrics: dict,
                      evidence: list, score: dict) -> str:
    def dump(obj) -> str:
        return json.dumps(obj, indent=2, default=str, sort_keys=True)

    return USER_TEMPLATE.format(
        persona=dump(persona),
        signal=dump(signal),
        metrics=dump(metrics),
        evidence=dump(evidence),
        score=dump(score),
    )
