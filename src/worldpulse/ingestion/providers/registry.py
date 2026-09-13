"""Provider registry -- turns `EVENT_PROVIDERS` into live adapters.

This is the single place that decides which event sources run. It:

  * reads `settings.event_providers` (comma-separated; default
    `"gdelt,usgs,eonet,gdacs"` -- the four feeds needing no key at all);
  * refuses paid providers when `WORLDPULSE_MODE=free` (the default);
  * instantiates only providers whose `is_available()` is True;
  * logs every skip with the reason, so a missing optional free key is a
    visible, explainable no-op rather than a crash or a silent gap.

`get_provider_health()` returns a `ProviderHealth` for *every* known
provider (not just the active ones) so `/health/providers` can report
DISABLED as a normal state.

Context providers (FRED, EIA) are intentionally NOT event providers and
are reached through `get_context_providers()` instead -- they can never
appear in `get_active_providers()`.
"""
from __future__ import annotations

import logging
import threading
from typing import Callable

from worldpulse.config import PAID_PROVIDERS, settings
from worldpulse.ingestion.providers.acled import ACLEDProvider
from worldpulse.ingestion.providers.base import ContextDataProvider, ProviderHealth, WorldEventProvider
from worldpulse.ingestion.providers.eia import EIAProvider
from worldpulse.ingestion.providers.eonet import EONETProvider
from worldpulse.ingestion.providers.firms import FIRMSProvider
from worldpulse.ingestion.providers.fred import FREDProvider
from worldpulse.ingestion.providers.gdacs import GDACSProvider
from worldpulse.ingestion.providers.gdelt import GDELTProvider
from worldpulse.ingestion.providers.usgs import USGSProvider
from worldpulse.ingestion.providers.worldmonitor import SyntheticEventProvider, WorldMonitorProvider

logger = logging.getLogger(__name__)

#: name -> zero-arg factory. Registration order here is also the order
#: providers are fetched in.
EVENT_PROVIDER_FACTORIES: dict[str, Callable[[], WorldEventProvider]] = {
    "gdelt": GDELTProvider,
    "usgs": USGSProvider,
    "eonet": EONETProvider,
    "gdacs": GDACSProvider,
    "firms": FIRMSProvider,
    "acled": ACLEDProvider,
    "worldmonitor": WorldMonitorProvider,
    "synthetic": SyntheticEventProvider,
}

CONTEXT_PROVIDER_FACTORIES: dict[str, Callable[[], ContextDataProvider]] = {
    "fred": FREDProvider,
    "eia": EIAProvider,
}

#: Providers that work with no credentials of any kind.
NO_KEY_PROVIDERS = frozenset({"gdelt", "usgs", "eonet", "gdacs", "synthetic"})

#: Providers needing a FREE registration key.
FREE_KEY_PROVIDERS = frozenset({"firms", "acled", "fred", "eia"})

_lock = threading.Lock()
_instances: dict[str, WorldEventProvider] = {}
_context_instances: dict[str, ContextDataProvider] = {}
_skips: dict[str, str] = {}


def reset_registry() -> None:
    """Drop cached instances. Used by tests that change settings/env."""
    with _lock:
        _instances.clear()
        _context_instances.clear()
        _skips.clear()


def _instantiate(name: str) -> WorldEventProvider | None:
    factory = EVENT_PROVIDER_FACTORIES.get(name)
    if factory is None:
        if name in CONTEXT_PROVIDER_FACTORIES:
            _skips[name] = (
                f"'{name}' is a context/feature provider (time series), not an event source; "
                "remove it from EVENT_PROVIDERS -- it is reached via get_context_providers()."
            )
        else:
            _skips[name] = (
                f"unknown provider '{name}'. Known: "
                f"{', '.join(sorted(EVENT_PROVIDER_FACTORIES))}"
            )
        logger.warning("provider registry: %s", _skips[name])
        return None

    if settings.is_free_mode and name in PAID_PROVIDERS:
        _skips[name] = (
            f"'{name}' requires a paid subscription and WORLDPULSE_MODE=free; skipped. "
            "Set WORLDPULSE_MODE=paid to enable it."
        )
        logger.info("provider registry: %s", _skips[name])
        return None

    try:
        provider = factory()
    except Exception as exc:  # noqa: BLE001 - a broken adapter must not break startup
        _skips[name] = f"'{name}' failed to construct: {exc}"
        logger.warning("provider registry: %s", _skips[name])
        return None

    if not provider.is_available():
        reason = provider.disabled_reason() or f"'{name}' reported itself unavailable"
        _skips[name] = reason
        provider.health.available = False
        provider.health.disabled_reason = reason
        logger.info("provider registry: %s", reason)
        # Cache the instance anyway so /health/providers can report it as
        # DISABLED with its reason.
        _instances[name] = provider
        return None

    provider.health.available = True
    provider.health.disabled_reason = None
    _instances[name] = provider
    return provider


def get_active_providers() -> list[WorldEventProvider]:
    """Instantiated, available event providers, in `EVENT_PROVIDERS` order.

    Never raises: an unavailable or unknown provider is skipped with a
    logged reason. Returning an empty list is a legitimate (if useless)
    outcome, e.g. `EVENT_PROVIDERS=worldmonitor` with no key.
    """
    with _lock:
        requested = settings.provider_names()
        active: list[WorldEventProvider] = []
        for name in requested:
            cached = _instances.get(name)
            if cached is not None and name not in _skips:
                active.append(cached)
                continue
            if name in _skips:
                continue
            provider = _instantiate(name)
            if provider is not None:
                active.append(provider)

        if not active:
            logger.warning(
                "provider registry: no active event providers from EVENT_PROVIDERS=%r "
                "(skips: %s)", settings.event_providers, _skips or "none",
            )
        else:
            logger.info("provider registry: active providers = %s",
                        [p.name for p in active])
        return active


def get_provider(name: str) -> WorldEventProvider | None:
    """Fetch (and cache) one provider by name, or None if unavailable."""
    with _lock:
        if name in _instances and name not in _skips:
            return _instances[name]
        if name in _skips:
            return None
        return _instantiate(name)


def get_context_providers() -> list[ContextDataProvider]:
    """Available context/feature providers (FRED, EIA). Never event sources."""
    with _lock:
        out: list[ContextDataProvider] = []
        for name, factory in CONTEXT_PROVIDER_FACTORIES.items():
            provider = _context_instances.get(name)
            if provider is None:
                try:
                    provider = factory()
                except Exception as exc:  # noqa: BLE001
                    logger.warning("provider registry: context provider '%s' failed: %s", name, exc)
                    continue
                _context_instances[name] = provider
            if provider.is_available():
                out.append(provider)
            else:
                logger.info("provider registry: %s", provider.disabled_reason())
        return out


def get_provider_health() -> list[ProviderHealth]:
    """Health for every known provider, including unselected/disabled ones.

    A provider that is not in `EVENT_PROVIDERS` is reported with
    `available=False` and a "not selected" reason; a selected provider
    missing its key is reported DISABLED with the key hint. Neither is an
    error condition.
    """
    # Ensure selection has been evaluated at least once.
    get_active_providers()
    requested = set(settings.provider_names())

    out: list[ProviderHealth] = []
    with _lock:
        for name, factory in EVENT_PROVIDER_FACTORIES.items():
            provider = _instances.get(name)
            if provider is not None:
                health = provider.health
                if name not in requested:
                    health.available = False
                    health.disabled_reason = f"'{name}' not listed in EVENT_PROVIDERS"
                out.append(health)
                continue

            health = ProviderHealth(provider=name, available=False)
            if name not in requested:
                paid_note = " (paid, optional)" if name in PAID_PROVIDERS else ""
                health.disabled_reason = f"'{name}' not listed in EVENT_PROVIDERS{paid_note}"
            else:
                health.disabled_reason = _skips.get(name, "not instantiated")
            out.append(health)

        for name, factory in CONTEXT_PROVIDER_FACTORIES.items():
            provider = _context_instances.get(name)
            if provider is None:
                try:
                    provider = factory()
                    _context_instances[name] = provider
                except Exception as exc:  # noqa: BLE001
                    out.append(ProviderHealth(provider=name, available=False,
                                              disabled_reason=f"construction failed: {exc}"))
                    continue
            health = provider.health
            health.available = provider.is_available()
            health.disabled_reason = provider.disabled_reason() or (
                "context/feature provider (time series, not events)"
                if health.available else provider.disabled_reason()
            )
            out.append(health)
    return out


def get_skips() -> dict[str, str]:
    """name -> reason, for every provider skipped during selection."""
    get_active_providers()
    return dict(_skips)


def provider_cost_groups() -> dict[str, list[str]]:
    """Documentation helper: providers grouped by what they cost."""
    return {
        "no_key_required": sorted(NO_KEY_PROVIDERS),
        "free_registration_key": sorted(FREE_KEY_PROVIDERS),
        "optional_paid": sorted(PAID_PROVIDERS),
    }
