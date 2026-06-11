"""Offline geocoder + autocomplete suggestions (local POI-name index)."""
from __future__ import annotations

import pytest

from discoverroute import config

pois_available = pytest.mark.skipif(
    not config.POIS_PATH.exists(), reason="POI table not built"
)


@pois_available
def test_suggest_finds_landmarks():
    from discoverroute.routing.geocode import suggest
    assert "Jardin du Luxembourg" in suggest("jardin du lux")
    assert any("Eiffel" in s for s in suggest("eiffel"))


@pois_available
def test_suggest_abstains_on_noise():
    from discoverroute.routing.geocode import suggest
    assert suggest("xq") == ()
    assert suggest("") == ()


@pois_available
def test_suggestion_round_trips_to_geocode():
    """Every suggestion must be resolvable by the local geocoder (in Paris)."""
    from discoverroute.routing.geocode import local_geocode, suggest
    for name in suggest("jardin du lux")[:3]:
        pt = local_geocode(name)
        assert pt is not None and config.in_paris(*pt)
