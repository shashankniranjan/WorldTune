"""Explanation layer.

`TemplatedExplainer` is the default and needs no API key, no network and no
model. It fills summary / why_it_matters / drivers / risks /
recommended_action from metrics that were *already computed* by the trend,
trajectory and ranking modules. It cannot invent a number because it has no
mechanism for producing one -- every figure it prints is formatted from a
value it was handed.

`LLMExplainer` is a pluggable skeleton (OpenAI-compatible chat completions)
used only when `LLM_API_KEY` is configured. It receives the same
already-computed payload and is instructed to cite nothing else. If it fails,
returns malformed JSON, or omits a key, it falls back to the templated
output rather than surfacing a broken card -- an explanation layer must never
be able to take the product down.

`get_explainer()` is the only thing callers should use.
"""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field

from app.config import settings
from app.llm.prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)


@dataclass
class Explanation:
    summary: str = ""
    why_it_matters: str = ""
    drivers: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    recommended_action: str = ""
    generated_by: str = "templated"

    def to_dict(self) -> dict:
        return asdict(self)


class Explainer(ABC):
    name = "explainer"

    @abstractmethod
    def explain(self, *, persona: dict, signal: dict, metrics: dict,
                evidence: list, score: dict) -> Explanation: ...


def _pct(value, digits: int = 1) -> str:
    try:
        return f"{float(value) * 100:+.{digits}f}%"
    except (TypeError, ValueError):
        return "n/a"


class TemplatedExplainer(Explainer):
    """Deterministic, offline, no key. The default."""

    name = "templated"

    def explain(self, *, persona: dict, signal: dict, metrics: dict,
                evidence: list, score: dict) -> Explanation:
        domain = signal.get("domain", "")
        label = signal.get("label") or signal.get("entity_id", "this signal")
        return (self._financial(persona, signal, metrics, evidence, score, label)
                if domain == "financial"
                else self._career(persona, signal, metrics, evidence, score, label))

    # -- financial -----------------------------------------------------------
    def _financial(self, persona, signal, metrics, evidence, score, label) -> Explanation:
        change_7d = metrics.get("change_7d", 0.0)
        change_24h = metrics.get("change_24h", 0.0)
        direction = metrics.get("direction", "neutral")
        probability = metrics.get("probability", 0.5)
        horizon = metrics.get("horizon_days", 7)
        sentiment = metrics.get("news_sentiment", 0.0)
        news_count = metrics.get("news_count", 0)

        summary = (f"{label} moved {_pct(change_24h)} in 24h and {_pct(change_7d)} over 7 days, "
                   f"with {news_count} related headline(s) in the window.")

        watchlist = [w.upper() for w in persona.get("watchlist", [])]
        # Match on the TICKER (entity_id), not the display label: the
        # watchlist holds "BTC" while the label is "Bitcoin", so comparing
        # labels silently never matches.
        if (signal.get("entity_id") or label).upper() in watchlist:
            why = f"{label} is on your watchlist, so this is a direct position-relevant move."
        elif signal.get("sector") and signal["sector"] in persona.get("sectors", []):
            why = (f"{label} sits in {signal['sector']}, one of the sectors you track, "
                   f"so it moves your broader exposure rather than a single holding.")
        else:
            why = f"{label} connects to your stated interests through {signal.get('sector', 'the technology complex')}."

        drivers = [f"7-day change {_pct(change_7d)}"]
        if metrics.get("momentum") is not None:
            drivers.append(f"EWMA momentum {_pct(metrics['momentum'], 2)}")
        if abs(float(sentiment or 0)) > 0.05:
            drivers.append(f"news tone {float(sentiment):+.2f} across {news_count} headline(s)")
        if metrics.get("volume_zscore"):
            drivers.append(f"volume z-score {float(metrics['volume_zscore']):+.2f}")

        risks = [
            f"The {direction} read is only {float(probability) * 100:.0f}% probable over {horizon} days.",
            "Directional signal only -- no price target, and no profitability claim.",
        ]
        if float(metrics.get("realized_volatility") or 0) > 0.6:
            risks.append(f"Realized volatility is high ({float(metrics['realized_volatility']):.0%} annualized).")

        action = (f"Review your {label} exposure against a {direction} {horizon}-day read; "
                  f"treat it as one input, not a trade instruction.")
        return Explanation(summary, why, drivers[:4], risks[:3], action, "templated")

    # -- career --------------------------------------------------------------
    def _career(self, persona, signal, metrics, evidence, score, label) -> Explanation:
        change_7d = metrics.get("change_7d", 0.0)
        change_30d = metrics.get("change_30d", 0.0)
        share = metrics.get("skill_share", 0.0)
        mentions = metrics.get("skill_mentions", 0)
        job_count = metrics.get("job_count", 0)
        direction = metrics.get("direction", "stable")

        summary = (f"{label} appears in {mentions} of {job_count} tracked postings "
                   f"({float(share) * 100:.0f}% share), {_pct(change_30d)} over 30 days.")

        has_it = label.lower() in {s.lower() for s in persona.get("skills", [])}
        target = ", ".join(persona.get("target_roles", [])[:2]) or "your target roles"
        if has_it:
            why = (f"You already list {label}, so its {direction} demand affects how your "
                   f"current profile reads to hiring teams for {target}.")
        else:
            why = (f"You do not list {label} yet, and it is {direction} in postings for "
                   f"{target} -- this is a concrete gap you could close.")

        drivers = [f"7-day change {_pct(change_7d)}", f"30-day change {_pct(change_30d)}"]
        if metrics.get("acceleration"):
            drivers.append(f"acceleration {float(metrics['acceleration']):+.4f}")
        if metrics.get("tech_velocity"):
            drivers.append(f"technology activity {_pct(metrics['tech_velocity'])}")

        risks = [
            f"Based on {job_count} tracked postings, which is a sample, not the whole market.",
            "Posting-text frequency measures what employers write, not what they pay for.",
        ]
        action = (f"Spend one focused session on {label} this week"
                  if not has_it else
                  f"Add a concrete {label} outcome to the top of your CV")
        action += f" -- it is the strongest {direction} signal against {target}."
        return Explanation(summary, why, drivers[:4], risks[:2], action, "templated")


class LLMExplainer(Explainer):
    """OpenAI-compatible chat-completions explainer. Used only with a key set.

    Deliberately thin: it adds phrasing on top of the same payload the
    templated explainer receives, and any failure degrades to that explainer.
    """

    name = "llm"

    def __init__(self, fallback: Explainer | None = None, client=None):
        self._fallback = fallback or TemplatedExplainer()
        self._client = client

    def is_available(self) -> bool:
        return bool(settings.llm_api_key)

    def explain(self, *, persona: dict, signal: dict, metrics: dict,
                evidence: list, score: dict) -> Explanation:
        if not self.is_available():
            return self._fallback.explain(persona=persona, signal=signal, metrics=metrics,
                                          evidence=evidence, score=score)
        try:
            payload = self._call_model(
                build_user_prompt(persona=persona, signal=signal, metrics=metrics,
                                  evidence=evidence, score=score)
            )
            return Explanation(
                summary=str(payload["summary"]),
                why_it_matters=str(payload["why_it_matters"]),
                drivers=[str(d) for d in payload.get("drivers", [])],
                risks=[str(r) for r in payload.get("risks", [])],
                recommended_action=str(payload["recommended_action"]),
                generated_by=f"llm:{settings.llm_model}",
            )
        except Exception as exc:
            logger.warning("LLM explainer failed (%s); falling back to templated", exc)
            return self._fallback.explain(persona=persona, signal=signal, metrics=metrics,
                                          evidence=evidence, score=score)

    def _call_model(self, user_prompt: str) -> dict:
        from app.providers.http import request_with_retry

        response = request_with_retry(
            f"{settings.llm_base_url.rstrip('/')}/chat/completions",
            method="POST",
            headers={"Authorization": f"Bearer {settings.llm_api_key}",
                     "Content-Type": "application/json"},
            client=self._client,
        ) if self._client is not None else _post_json(
            f"{settings.llm_base_url.rstrip('/')}/chat/completions",
            {
                "model": settings.llm_model,
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            },
        )
        body = response if isinstance(response, dict) else response.json()
        content = body["choices"][0]["message"]["content"]
        return json.loads(content)


def _post_json(url: str, payload: dict) -> dict:
    import httpx

    from app.providers.http import build_client

    with build_client(timeout=settings.http_timeout_seconds) as client:
        resp: httpx.Response = client.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
        )
        resp.raise_for_status()
        return resp.json()


def get_explainer() -> Explainer:
    """Single entry point. LLM only when a key is configured."""
    if settings.llm_api_key:
        return LLMExplainer(fallback=TemplatedExplainer())
    return TemplatedExplainer()
