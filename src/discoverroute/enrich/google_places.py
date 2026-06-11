"""Optional live verification of the FINAL selected stops via Google Places.

Design constraints (and why this module looks the way it does):
  * Google's ToS prohibit storing Places content (only place_id is cacheable),
    so this runs per-request on the ~8 chosen stops only and nothing is
    persisted. OSM remains the storable base for candidates and routing.
  * Opening-hours fields bill at the Enterprise SKU (1,000 free events/month
    => ~125 free routes). Verifying only the final stops keeps cost bounded.
  * Entirely optional: without ``GOOGLE_MAPS_API_KEY`` in the environment this
    module is a silent no-op and the app stays fully offline.

Each verified POI gains ``.live_status`` (True=open now, False=closed) and
``.live_rating`` — consumed by the narration template's badges.
"""
from __future__ import annotations

import json
import logging
import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("discoverroute")

_ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
_FIELDS = ("places.id,places.displayName,places.businessStatus,"
           "places.currentOpeningHours.openNow,places.rating")
_TIMEOUT_S = 3.0
_MAX_STOPS = 12


def api_key() -> str | None:
    return os.environ.get("GOOGLE_MAPS_API_KEY") or None


def _verify_one(poi, key: str) -> None:
    """Look up one POI by name near its coordinates; annotate it in place."""
    name = getattr(poi, "name", None)
    if not name:
        return
    body = json.dumps({
        "textQuery": name,
        "locationBias": {"circle": {
            "center": {"latitude": poi.lat, "longitude": poi.lon},
            "radius": 150.0,
        }},
        "maxResultCount": 1,
    }).encode()
    req = urllib.request.Request(
        _ENDPOINT, data=body, method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": key,
            "X-Goog-FieldMask": _FIELDS,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_S) as resp:
            data = json.loads(resp.read().decode())
    except Exception as exc:  # noqa: BLE001 - enrichment must never break a route
        logger.warning("google verify failed for %r: %s: %s",
                       name, type(exc).__name__, exc)
        return
    places = data.get("places") or []
    if not places:
        return
    place = places[0]
    if place.get("businessStatus") == "CLOSED_PERMANENTLY":
        poi.live_status = False
        return
    open_now = (place.get("currentOpeningHours") or {}).get("openNow")
    if open_now is not None:
        poi.live_status = bool(open_now)
    rating = place.get("rating")
    if rating is not None:
        poi.live_rating = float(rating)


def verify_stops(pois: list) -> bool:
    """Live-verify up to _MAX_STOPS POIs in parallel. Returns True if any ran."""
    key = api_key()
    if not key or not pois:
        return False
    batch = pois[:_MAX_STOPS]
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda p: _verify_one(p, key), batch))
    return True
