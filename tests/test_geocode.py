"""Offline geocoding tests: local POI-name index + offline-mode behaviour.

Real names are picked from the parquet at test time (never hardcoded guesses),
except the app's two default inputs, which must resolve locally by contract.
"""
from __future__ import annotations

import math

import pandas as pd
import pytest

from discoverroute import config
from discoverroute.routing import geocode as gc
from discoverroute.routing.graph import RouteError, geocode_point

pytestmark = pytest.mark.skipif(
    not config.POIS_PATH.exists(),
    reason="POI table not built (run: python -m discoverroute.data.build_pois)",
)

# Known coordinates of the app's two default inputs.
REPUBLIQUE = (48.8674, 2.3636)
LUXEMBOURG = (48.8462, 2.3372)

GIBBERISH = "zzqx flurbington nonexistovia 9999"


def _named_pois() -> pd.DataFrame:
    from discoverroute.routing.pois import load_pois

    df = load_pois()
    return df[df["name"].notna()]


def _pick_name(require_accent: bool = False) -> str:
    """A real, distinctive POI name from the table (best-documented first)."""
    df = _named_pois().sort_values(["confidence", "n_tags"], ascending=False)
    for name in df["name"]:
        norm = gc._normalize(name)
        tokens = norm.split()
        if len(tokens) < 2 or not any(len(t) >= 4 for t in tokens):
            continue  # too short/ambiguous to be a fair test query
        if tokens[-1] in ("paris", "france"):
            continue  # would interact with suffix stripping; pick another
        if require_accent and all(ord(c) < 128 for c in name):
            continue
        return name
    pytest.skip("no suitable POI name found in the table")


def _coords_for_name(name: str) -> set[tuple[float, float]]:
    """All (lat, lon) rows whose normalised name equals the query's."""
    df = _named_pois()
    norm = gc._normalize(name)
    mask = df["name"].map(lambda n: gc._normalize(n) == norm)
    return {(float(r.lat), float(r.lon)) for r in df[mask].itertuples()}


def _dist_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    dlat = (a[0] - b[0]) * 110_540.0
    dlon = (a[1] - b[1]) * 111_320.0 * math.cos(math.radians(a[0]))
    return math.hypot(dlat, dlon)


def test_exact_name_match():
    name = _pick_name()
    result = gc.local_geocode(name)
    assert result is not None
    assert result in _coords_for_name(name)


def test_accent_and_case_insensitive():
    name = _pick_name(require_accent=True)
    expected = gc.local_geocode(name)
    assert expected is not None
    # Uppercased and accent-stripped versions of the same name still resolve.
    assert gc.local_geocode(name.upper()) == expected
    assert gc.local_geocode(gc._normalize(name)) == expected


def test_paris_suffix_stripped():
    name = _pick_name()
    expected = gc.local_geocode(name)
    assert expected is not None
    assert gc.local_geocode(f"{name}, Paris") == expected
    assert gc.local_geocode(f"{name} Paris") == expected
    assert gc.local_geocode(f"{name}, Paris, France") == expected


def test_no_match_returns_none():
    assert gc.local_geocode(GIBBERISH) is None
    assert gc.local_geocode("") is None
    assert gc.local_geocode("de la") is None  # short fragments: too ambiguous


def test_offline_mode_raises_for_unmatchable(monkeypatch):
    monkeypatch.setenv(config.OFFLINE_ENV_VAR, "1")
    with pytest.raises(RouteError, match="offline"):
        geocode_point(GIBBERISH)


def test_latlon_path_unaffected_offline(monkeypatch):
    monkeypatch.setenv(config.OFFLINE_ENV_VAR, "1")
    assert geocode_point("48.8674, 2.3636") == (48.8674, 2.3636)


@pytest.mark.parametrize(
    "query,known",
    [
        ("Place de la République, Paris", REPUBLIQUE),
        ("Jardin du Luxembourg, Paris", LUXEMBOURG),
    ],
)
def test_app_defaults_resolve_locally(query, known, monkeypatch):
    # Pure offline path: must work with the Nominatim fallback disabled.
    monkeypatch.setenv(config.OFFLINE_ENV_VAR, "1")
    local = gc.local_geocode(query)
    assert local is not None, f"default input {query!r} not in local index"
    assert config.in_paris(*local)
    assert _dist_m(local, known) < 1500, f"{query!r} resolved far away: {local}"
    # And the full geocode_point pipeline (bounds check included) agrees.
    assert geocode_point(query) == local
