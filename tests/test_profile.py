"""Brick 5 tests: persistent taste profile blended with trip mood (P1-1)."""
from __future__ import annotations

import pytest

from discoverroute import config

pytest.importorskip("sentence_transformers")

from discoverroute.interpret import profile as prof


def test_empty_profile_has_no_affinity():
    assert prof.profile_affinity(prof.empty_profile()) is None
    assert prof.profile_affinity({}) is None


def test_saved_places_boost_their_categories():
    p = {"standing_text": "", "saved_categories": ["park_garden", "park_garden"]}
    aff = prof.profile_affinity(p)
    assert aff["park_garden"] > aff["bar_pub"]


def test_standing_text_shapes_affinity():
    p = {"standing_text": "I love quiet bookshops and libraries", "saved_categories": []}
    aff = prof.profile_affinity(p)
    assert aff["bookshop"] > aff["bar_pub"]
    assert aff["library"] > aff["restaurant"]


def test_effective_blend_modes():
    park_profile = {"standing_text": "", "saved_categories": ["park_garden"]}
    # profile only
    w_prof = prof.effective_weights(park_profile, trip_vibe="")
    assert w_prof.category_affinity["park_garden"] > w_prof.category_affinity["bar_pub"]
    # trip mood only (no profile)
    w_trip = prof.effective_weights({}, trip_vibe="lively bars and nightlife")
    assert w_trip.category_affinity["bar_pub"] > w_trip.category_affinity["park_garden"]
    # neither -> uniform
    w_none = prof.effective_weights({}, trip_vibe="")
    assert set(w_none.category_affinity.values()) == {1.0}


data_ready = pytest.mark.skipif(
    not (config.GRAPH_WALK_PATH.exists() and config.POIS_PATH.exists()),
    reason="Graph or POI table not built",
)


@data_ready
def test_profile_shifts_route():
    """Editing the profile measurably shifts the route (the P1-1 DoD)."""
    from discoverroute.pipeline import plan_route
    a, b = "Place de la République, Paris", "Jardin du Luxembourg, Paris"
    none = plan_route(a, b, budget=0.7)
    booky = plan_route(a, b, budget=0.7,
                       profile={"standing_text": "quiet libraries and bookshops",
                                "saved_categories": ["library", "bookshop"]})
    assert booky.discovery is not None
    assert {p.osm_id for p in none.pois} != {p.osm_id for p in booky.pois}
