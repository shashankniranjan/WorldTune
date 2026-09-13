"""Event/context provider adapters.

Every real-world data source WorldPulse can ingest from lives here behind
one of two ports defined in `base.py`:

  * `WorldEventProvider` -- discrete events -> `WorldEvent`
    (GDELT, USGS, EONET, GDACS, FIRMS, ACLED, World Monitor, synthetic)
  * `ContextDataProvider` -- macro/energy time series -> `SeriesPoint`
    (FRED, EIA); deliberately NOT event sources.

`registry.get_active_providers()` is the only thing the rest of the
pipeline needs to know about.
"""
from worldpulse.ingestion.providers.base import (  # noqa: F401
    ContextDataProvider,
    ProviderHealth,
    SeriesPoint,
    WorldEventProvider,
    haversine_km,
)

__all__ = [
    "ContextDataProvider",
    "ProviderHealth",
    "SeriesPoint",
    "WorldEventProvider",
    "haversine_km",
]
