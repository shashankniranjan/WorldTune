"""Hand-built fixture payloads matching each provider's REAL response shape.

Live network calls cannot be part of an automated test suite: they are
non-deterministic, they fail in CI/sandboxes, and they make the tests a
liability rather than a safety net. So every provider test drives the
adapter through an `httpx.MockTransport` whose responses are the payload
shapes documented for each upstream API (see each provider module's
docstring for the endpoint and schema these mirror).

Live *reachability* is verified separately, by hand, with
`scripts/verify_live_providers.py`.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import httpx

# A fixed window every fixture's timestamps fall inside.
WINDOW_START = datetime(2024, 1, 14, tzinfo=timezone.utc)
WINDOW_END = datetime(2024, 1, 16, tzinfo=timezone.utc)

# 2024-01-15T12:00:00Z in epoch milliseconds, as USGS reports `time`.
USGS_EVENT_TIME_MS = 1_705_320_000_000


# --- GDELT DOC 2.0 `mode=artlist&format=json` ---------------------------

GDELT_DISASTER_ARTICLES = [
    {
        "url": "https://www.reuters.com/world/asia-pacific/taiwan-quake-2024-01-15/",
        "url_mobile": "",
        "title": "Powerful magnitude 6.1 earthquake strikes eastern Taiwan, damage reported",
        "seendate": "20240115T123000Z",
        "socialimage": "https://www.reuters.com/img/quake.jpg",
        "domain": "reuters.com",
        "language": "English",
        "sourcecountry": "United Kingdom",
    },
    {
        # Non-English: must be filtered out by the adapter.
        "url": "https://www.lemonde.fr/international/article/0115",
        "url_mobile": "",
        "title": "Un seisme frappe Taiwan",
        "seendate": "20240115T130000Z",
        "socialimage": "",
        "domain": "lemonde.fr",
        "language": "French",
        "sourcecountry": "France",
    },
]

GDELT_ENERGY_ARTICLES = [
    {
        "url": "https://apnews.com/article/middle-east-tanker-strike-0115",
        "url_mobile": "",
        "title": "Tanker attacked near Iran coast, oil shipments disrupted in Strait of Hormuz",
        "seendate": "20240115T081500Z",
        "socialimage": "",
        "domain": "apnews.com",
        "language": "English",
        "sourcecountry": "United States",
    },
]

#: The adapter issues one query per domain; a real DOC API call returns
#: results for that query only. Keyed on a distinctive phrase from each of
#: `gdelt.DOMAIN_QUERIES`.
GDELT_ARTLIST_BY_QUERY: dict[str, list[dict]] = {
    "earthquake": GDELT_DISASTER_ARTICLES,
    "pipeline explosion": GDELT_ENERGY_ARTICLES,
}


def _gdelt_response_for(query: str) -> dict:
    for marker, articles in GDELT_ARTLIST_BY_QUERY.items():
        if marker in query:
            return {"articles": articles}
    # Real behaviour for a query with no hits in the window.
    return {"articles": []}


# --- USGS FDSN event query / summary feed (GeoJSON) ---------------------

USGS_GEOJSON = {
    "type": "FeatureCollection",
    "metadata": {
        "generated": 1705324000000,
        "url": "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson",
        "title": "USGS Earthquakes",
        "status": 200,
        "api": "1.14.0",
        "count": 2,
    },
    "features": [
        {
            "type": "Feature",
            "properties": {
                "mag": 6.1,
                "place": "14 km SSE of Hualien City, Taiwan",
                "time": USGS_EVENT_TIME_MS,
                "updated": USGS_EVENT_TIME_MS + 600000,
                "tz": None,
                "url": "https://earthquake.usgs.gov/earthquakes/eventpage/us7000abcd",
                "detail": "https://earthquake.usgs.gov/fdsnws/event/1/query?eventid=us7000abcd",
                "felt": 1420,
                "cdi": 7.2,
                "mmi": 6.8,
                "alert": "orange",
                "status": "reviewed",
                "tsunami": 1,
                "sig": 812,
                "net": "us",
                "code": "7000abcd",
                "ids": ",us7000abcd,",
                "sources": ",us,",
                "types": ",dyfi,origin,phase-data,shakemap,",
                "nst": 118,
                "dmin": 0.512,
                "rms": 0.86,
                "gap": 21,
                "magType": "mww",
                "type": "earthquake",
                "title": "M 6.1 - 14 km SSE of Hualien City, Taiwan",
            },
            "geometry": {"type": "Point", "coordinates": [121.6015, 23.8312, 24.5]},
            "id": "us7000abcd",
        },
        {
            "type": "Feature",
            "properties": {
                "mag": 4.9,
                "place": "72 km W of Ferndale, California",
                "time": USGS_EVENT_TIME_MS + 3_600_000,
                "updated": USGS_EVENT_TIME_MS + 4_000_000,
                "url": "https://earthquake.usgs.gov/earthquakes/eventpage/nc73999999",
                "alert": None,
                "status": "automatic",
                "tsunami": 0,
                "sig": 368,
                "net": "nc",
                "code": "73999999",
                "magType": "mw",
                "type": "earthquake",
                "title": "M 4.9 - 72 km W of Ferndale, California",
            },
            "geometry": {"type": "Point", "coordinates": [-125.1, 40.35, 8.2]},
            "id": "nc73999999",
        },
    ],
}


# --- NASA EONET v3 `/api/v3/events` -------------------------------------

EONET_EVENTS = {
    "title": "EONET Events",
    "description": "Natural events from EONET.",
    "link": "https://eonet.gsfc.nasa.gov/api/v3/events",
    "events": [
        {
            "id": "EONET_6789",
            "title": "Earthquake - Hualien County, Taiwan",
            "description": "Magnitude 6.1 earthquake offshore eastern Taiwan.",
            "link": "https://eonet.gsfc.nasa.gov/api/v3/events/EONET_6789",
            "closed": None,
            "categories": [{"id": "earthquakes", "title": "Earthquakes"}],
            "sources": [
                {"id": "USGS", "url": "https://earthquake.usgs.gov/earthquakes/eventpage/us7000abcd"}
            ],
            "geometry": [
                {
                    "magnitudeValue": 6.1,
                    "magnitudeUnit": "mww",
                    "date": "2024-01-15T12:00:00Z",
                    "type": "Point",
                    "coordinates": [121.6, 23.83],
                }
            ],
        },
        {
            "id": "EONET_6790",
            "title": "Wildfire - Kimberley Region, Australia",
            "description": "",
            "link": "https://eonet.gsfc.nasa.gov/api/v3/events/EONET_6790",
            "closed": None,
            "categories": [{"id": "wildfires", "title": "Wildfires"}],
            "sources": [{"id": "NOAA_NHC", "url": "https://example.gov/fire/1"}],
            "geometry": [
                {
                    "magnitudeValue": 120000.0,
                    "magnitudeUnit": "acres",
                    "date": "2024-01-15T06:00:00Z",
                    "type": "Point",
                    "coordinates": [126.4, -17.2],
                }
            ],
        },
    ],
}


# --- GDACS `EVENTS4APP` (GeoJSON) ---------------------------------------

GDACS_EVENTS = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [121.62, 23.84]},
            "properties": {
                "eventtype": "EQ",
                "eventid": 1435678,
                "episodeid": 1,
                "eventname": "Hualien",
                "glide": "",
                "name": "Earthquake in Taiwan",
                "description": "Magnitude 6.1 earthquake",
                "htmldescription": "<b>Magnitude 6.1M</b>, Depth: 24.5km",
                "icon": "https://www.gdacs.org/images/gdacs_icons/maps/Orange/EQ.png",
                "iconoverall": "https://www.gdacs.org/images/gdacs_icons/maps/Orange/EQ.png",
                "url": {
                    "geometry": "https://www.gdacs.org/gdacsapi/api/polygons/getgeometry?eventtype=EQ&eventid=1435678",
                    "report": "https://www.gdacs.org/report.aspx?eventtype=EQ&eventid=1435678",
                    "details": "https://www.gdacs.org/gdacsapi/api/events/geteventdata?eventtype=EQ&eventid=1435678",
                },
                "alertlevel": "Orange",
                "alertscore": 2,
                "episodealertlevel": "Orange",
                "episodealertscore": 2,
                "istemporary": "false",
                "iscurrent": "true",
                "country": "Taiwan",
                "iso3": "TWN",
                "fromdate": "2024-01-15T12:00:00",
                "todate": "2024-01-15T12:00:00",
                "datemodified": "2024-01-15T12:40:00",
                "severitydata": {
                    "severity": 6.1,
                    "severitytext": "Magnitude 6.1M, Depth:24.5km",
                    "severityunit": "M",
                },
                "source": "USGS",
            },
        }
    ],
}


# --- NASA FIRMS area CSV -------------------------------------------------

FIRMS_CSV = (
    "latitude,longitude,bright_ti4,scan,track,acq_date,acq_time,satellite,instrument,"
    "confidence,version,bright_ti5,frp,daynight\n"
    "-17.201,126.401,340.1,0.39,0.36,2024-01-15,1200,N,VIIRS,h,2.0NRT,295.2,45.6,D\n"
    "-17.205,126.412,352.8,0.39,0.36,2024-01-15,1200,N,VIIRS,h,2.0NRT,298.1,88.2,D\n"
    "-17.198,126.398,331.4,0.40,0.37,2024-01-15,1202,N,VIIRS,n,2.0NRT,292.7,31.9,D\n"
    "-17.212,126.420,367.9,0.41,0.37,2024-01-15,1202,N,VIIRS,h,2.0NRT,301.4,132.5,D\n"
    "-17.190,126.390,344.2,0.39,0.36,2024-01-15,1204,N,VIIRS,h,2.0NRT,296.3,58.1,D\n"
    "-17.221,126.431,359.6,0.42,0.38,2024-01-15,1204,N,VIIRS,h,2.0NRT,299.9,101.3,D\n"
    "-17.185,126.383,328.7,0.38,0.35,2024-01-15,1206,N,VIIRS,n,2.0NRT,291.5,27.4,D\n"
    "-17.230,126.442,371.2,0.43,0.39,2024-01-15,1206,N,VIIRS,h,2.0NRT,303.8,156.7,D\n"
)


# --- ACLED OAuth + `/api/acled/read` ------------------------------------

ACLED_TOKEN = {
    "access_token": "test-access-token",
    "refresh_token": "test-refresh-token",
    "token_type": "Bearer",
    "expires_in": 3600,
}

ACLED_READ = {
    "status": 200,
    "success": True,
    "last_update": 240,
    "count": 1,
    "data": [
        {
            "event_id_cnty": "YEM12345",
            "event_date": "2024-01-15",
            "year": "2024",
            "time_precision": "1",
            "disorder_type": "Political violence",
            "event_type": "Explosions/Remote violence",
            "sub_event_type": "Air/drone strike",
            "actor1": "Military Forces of the United States (2021-)",
            "assoc_actor_1": "",
            "actor2": "Houthi Movement",
            "country": "Yemen",
            "iso": "887",
            "region": "Middle East",
            "admin1": "Sanaa",
            "admin2": "Sanaa",
            "location": "Sanaa",
            "latitude": "15.3547",
            "longitude": "44.2066",
            "geo_precision": "1",
            "source": "Reuters",
            "source_scale": "International",
            "notes": "Coalition forces conducted a strike on a Houthi missile site.",
            "fatalities": "12",
            "tags": "",
            "timestamp": "1705400000",
        }
    ],
}


# --- Binance klines ------------------------------------------------------

BINANCE_KLINES = [
    [
        1705320000000, "42500.10", "42800.00", "42300.55", "42750.20", "1523.4512",
        1705323599999, "64821000.12", 51234, "760.1200", "32410500.05", "0",
    ],
    [
        1705323600000, "42750.20", "43100.00", "42700.00", "43050.75", "1789.2201",
        1705327199999, "76912000.44", 60112, "890.4400", "38455000.22", "0",
    ],
]


# --- Stooq daily CSV ----------------------------------------------------

STOOQ_CSV = (
    "Date,Open,High,Low,Close,Volume\n"
    "2024-01-12,4780.21,4802.40,4775.10,4783.83,2145678000\n"
    "2024-01-15,4785.00,4810.60,4780.25,4807.12,1987654000\n"
)


# --- Mock transports ----------------------------------------------------

def _json(payload) -> httpx.Response:
    return httpx.Response(200, content=json.dumps(payload),
                          headers={"Content-Type": "application/json"})


def _text(body: str, content_type: str = "text/csv") -> httpx.Response:
    return httpx.Response(200, content=body, headers={"Content-Type": content_type})


def make_transport() -> httpx.MockTransport:
    """One transport that answers every provider's real URL shape.

    Routing is by host + path so the adapters' actual request URLs are
    exercised: a typo in an endpoint path shows up as an unrouted-request
    assertion failure rather than passing silently.
    """
    def handler(request: httpx.Request) -> httpx.Response:
        host = request.url.host
        path = request.url.path

        if host == "api.gdeltproject.org" and path.startswith("/api/v2/doc/doc"):
            # The real DOC API answers per-query, and the adapter issues
            # one query per event domain, so the fixture must too --
            # otherwise every article would be attributed to whichever
            # domain happens to be queried first.
            return _json(_gdelt_response_for(request.url.params.get("query", "")))
        if host == "earthquake.usgs.gov":
            if path.startswith("/fdsnws/event/1/query") or path.startswith("/earthquakes/feed"):
                return _json(USGS_GEOJSON)
        if host == "eonet.gsfc.nasa.gov" and path.startswith("/api/v3/events"):
            return _json(EONET_EVENTS)
        if host == "www.gdacs.org":
            if "geteventlist" in path:
                return _json(GDACS_EVENTS)
            if path.endswith("rss.xml"):
                return _text(GDACS_RSS, "application/rss+xml")
        if host == "firms.modaps.eosdis.nasa.gov" and path.startswith("/api/area/csv"):
            return _text(FIRMS_CSV)
        if host == "acleddata.com":
            if path.startswith("/oauth/token"):
                return _json(ACLED_TOKEN)
            if path.startswith("/api/acled/read"):
                return _json(ACLED_READ)
        if host == "api.binance.com" and path.startswith("/api/v3/klines"):
            return _json(BINANCE_KLINES)
        if host == "stooq.com" and path.startswith("/q/d/l/"):
            return _text(STOOQ_CSV)
        if host == "api.stlouisfed.org" and path.startswith("/fred/series/observations"):
            return _json(FRED_OBSERVATIONS)
        if host == "api.eia.gov" and path.startswith("/v2/seriesid/"):
            return _json(EIA_SERIES)

        raise AssertionError(f"unrouted request in test: {request.method} {request.url}")

    return httpx.MockTransport(handler)


def make_client() -> httpx.Client:
    """An `httpx.Client` bound to the mock transport (no network at all)."""
    return httpx.Client(transport=make_transport(), base_url="https://example.invalid")


# --- Remaining fixtures referenced above --------------------------------

GDACS_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:gdacs="http://www.gdacs.org" xmlns:geo="http://www.w3.org/2003/01/geo/wgs84_pos#">
  <channel>
    <title>GDACS RSS feed</title>
    <item>
      <title>Orange earthquake alert in Taiwan 15/01/2024 12:00 UTC</title>
      <link>https://www.gdacs.org/report.aspx?eventtype=EQ&amp;eventid=1435678</link>
      <description>Magnitude 6.1M, Depth: 24.5km</description>
      <pubDate>Mon, 15 Jan 2024 12:40:00 GMT</pubDate>
      <gdacs:eventtype>EQ</gdacs:eventtype>
      <gdacs:eventid>1435678</gdacs:eventid>
      <gdacs:alertlevel>Orange</gdacs:alertlevel>
      <gdacs:country>Taiwan</gdacs:country>
      <gdacs:fromdate>2024-01-15T12:00:00</gdacs:fromdate>
      <geo:lat>23.84</geo:lat>
      <geo:long>121.62</geo:long>
    </item>
  </channel>
</rss>
"""

FRED_OBSERVATIONS = {
    "realtime_start": "2024-01-16",
    "realtime_end": "2024-01-16",
    "observation_start": "2024-01-01",
    "observation_end": "2024-01-16",
    "units": "lin",
    "output_type": 1,
    "file_type": "json",
    "order_by": "observation_date",
    "sort_order": "asc",
    "count": 3,
    "offset": 0,
    "limit": 100000,
    "observations": [
        {"realtime_start": "2024-01-16", "realtime_end": "2024-01-16",
         "date": "2024-01-11", "value": "3.97"},
        {"realtime_start": "2024-01-16", "realtime_end": "2024-01-16",
         "date": "2024-01-12", "value": "3.95"},
        # FRED encodes a missing observation as "."
        {"realtime_start": "2024-01-16", "realtime_end": "2024-01-16",
         "date": "2024-01-15", "value": "."},
    ],
}

EIA_SERIES = {
    "response": {
        "total": 2,
        "dateFormat": "YYYY-MM-DD",
        "frequency": "weekly",
        "data": [
            {"period": "2024-01-05", "value": 431234, "units": "MBBL",
             "series": "PET.WCESTUS1.W", "series-description": "US crude stocks"},
            {"period": "2024-01-12", "value": 429876, "units": "MBBL",
             "series": "PET.WCESTUS1.W", "series-description": "US crude stocks"},
        ],
    },
    "apiVersion": "2.1.5",
}
