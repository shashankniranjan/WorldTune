"""Shared country-focus helpers for event providers.

`settings.country_focus` (env `COUNTRY_FOCUS`) narrows the free feeds to one
country instead of the global default. Providers apply it differently
depending on what their upstream API actually supports:

  * `gdelt.py`  -- server-side: appends `sourcecountry:<fips>` to every
    domain query (GDELT DOC 2.0 uses FIPS 10-4 country codes, not ISO).
  * `usgs.py`   -- server-side: adds a lat/lon bounding box to the FDSN
    query and the live summary-feed request.
  * `eonet.py`, `gdacs.py` -- neither API takes a country/region filter, so
    the provider fetches globally and filters the parsed results
    client-side using the bounding box + country-name check here.

This module only knows about a small hardcoded table (currently just
India); add more `CountryFocus` entries as more countries are needed.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from worldpulse.config import settings


@dataclass(frozen=True)
class CountryFocus:
    iso2: str
    name: str
    gdelt_fips: str  # GDELT DOC 2.0 `sourcecountry:` uses FIPS 10-4, not ISO
    # Bounding box, (min_lat, max_lat, min_lon, max_lon), generous enough to
    # cover the whole country plus near-border events (e.g. an Indian Ocean
    # earthquake that still matters to Indian markets).
    bbox: tuple[float, float, float, float]
    name_hints: tuple[str, ...]


_FOCUSES: dict[str, CountryFocus] = {
    "IN": CountryFocus(
        iso2="IN",
        name="India",
        gdelt_fips="IN",
        bbox=(5.0, 38.0, 66.0, 99.0),
        name_hints=("india", "indian", "delhi", "mumbai", "bengaluru", "bangalore",
                    "kolkata", "chennai", "hyderabad", "gujarat", "maharashtra",
                    "rajasthan", "punjab", "kashmir", "himalaya"),
    ),
}


def get_focus() -> Optional[CountryFocus]:
    """The active `CountryFocus`, or None if `COUNTRY_FOCUS` is unset/unknown."""
    code = (settings.country_focus or "").strip().upper()
    if not code:
        return None
    focus = _FOCUSES.get(code)
    if focus is None:
        return None
    return focus


def matches(focus: CountryFocus, *, lat: float | None = None, lon: float | None = None,
            text: str = "", countries: list[str] | None = None) -> bool:
    """True if a record's coordinates/text/country list falls in `focus`."""
    if lat is not None and lon is not None:
        min_lat, max_lat, min_lon, max_lon = focus.bbox
        if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
            return True
    if countries:
        for c in countries:
            if focus.name.lower() in c.lower() or c.upper() == focus.iso2:
                return True
    if text:
        lower = text.lower()
        if any(hint in lower for hint in focus.name_hints):
            return True
    return False
