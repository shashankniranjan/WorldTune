"""Registry of World Shift knowledge packs.

Adding a shift means adding one declarative module under ``packs/``. No
composer, schema or frontend change is required, and a shift with no pack still
renders through ``generic_pack``.

``armed-conflict-and-military-escalation`` is deliberately absent. It is served
by the frozen editorial path in ``world_shift_contract.py`` and is the quality
reference this layer is measured against, so it is not re-derived here.
"""
from __future__ import annotations

from .base import KnowledgePack
from .generic import generic_pack
from .packs import (
    ai_infrastructure,
    cloud_infrastructure,
    crypto_regulation,
    cybersecurity,
    india_digital_policy,
    inflation_and_rates,
    sanctions_and_economic_warfare,
    semiconductors,
)

PACKS: dict[str, KnowledgePack] = {
    pack.slug: pack
    for pack in (
        ai_infrastructure.PACK,
        cloud_infrastructure.PACK,
        crypto_regulation.PACK,
        cybersecurity.PACK,
        india_digital_policy.PACK,
        inflation_and_rates.PACK,
        sanctions_and_economic_warfare.PACK,
        semiconductors.PACK,
    )
}


def knowledge_for(slug: str, topic: str, category: str) -> KnowledgePack:
    """Return the pack for a shift, falling back to a category-shaped generic one."""
    pack = PACKS.get(slug)
    return pack if pack is not None else generic_pack(topic, category)


def has_pack(slug: str) -> bool:
    return slug in PACKS


__all__ = ["PACKS", "KnowledgePack", "knowledge_for", "has_pack", "generic_pack"]
