"""Brick 3 tests: end-to-end discovery routing against plain, on real data."""
from __future__ import annotations

import pytest

from discoverroute import config
from discoverroute.pipeline import plan_route

data_ready = pytest.mark.skipif(
    not (config.GRAPH_WALK_PATH.exists() and config.POIS_PATH.exists()),
    reason="Graph or POI table not built",
)

START = "Place de la République, Paris"
DEST = "Jardin du Luxembourg, Paris"


@data_ready
def test_budget_zero_is_plain_route():
    r = plan_route(START, DEST, budget=0.0)
    assert r.error is None
    assert r.discovery is None
    assert r.pois == []
    assert r.plain is not None


@data_ready
def test_discovery_respects_budget_and_detours():
    budget = 0.6
    r = plan_route(START, DEST, budget=budget, prefer_green=0.5, prefer_quiet=0.5)
    assert r.error is None
    assert r.plain is not None
    if r.discovery is not None:  # a detour was found
        assert len(r.pois) > 0
        # never exceeds (1 + budget) x the direct time (P0-3), small float slack
        assert r.discovery.time_s <= (1.0 + budget) * r.plain.time_s * 1.02
        # a discovery route is at least as long as the direct one
        assert r.discovery.distance_m >= r.plain.distance_m - 1.0
        # every named waypoint is a real POI carrying a category
        for p in r.pois:
            assert p.category in __import__(
                "discoverroute.data.taxonomy", fromlist=["CATEGORIES"]
            ).CATEGORIES


@data_ready
def test_out_of_bounds_clean_error():
    # Explicit London coordinates: deterministically outside the Paris bbox.
    # (A *name* like "London" may legitimately resolve to a Paris venue with
    # that name via the offline POI-name geocoder.)
    r = plan_route("51.5074, -0.1278", DEST, budget=0.5)
    assert r.error is not None
    assert r.discovery is None and r.plain is None


@data_ready
def test_alternatives_are_distinct():
    """P1-4: multiple route options are genuinely different sets of places."""
    r = plan_route(START, DEST, budget=0.6, vibe="quiet green wander",
                   n_alternatives=3)
    assert len(r.alternatives) >= 2
    sets = [{p.osm_id for p in a.pois} for a in r.alternatives]
    # the first two options should share little (distinct routes)
    overlap = len(sets[0] & sets[1]) / max(1, len(sets[0]))
    assert overlap < 0.5
