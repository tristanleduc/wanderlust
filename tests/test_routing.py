"""Brick 0 tests: plain routing, geocoding, and bounds handling."""
from __future__ import annotations

import pytest

from discoverroute import config
from discoverroute.routing import graph as g
from discoverroute.routing.graph import RouteError

# Known Paris points.
REPUBLIQUE = (48.8674, 2.3636)
LUXEMBOURG = (48.8462, 2.3372)
LONDON = (51.5074, -0.1278)  # out of bounds

graph_available = pytest.mark.skipif(
    not config.GRAPH_WALK_PATH.exists(),
    reason="Paris graph not built (run: python -m discoverroute.data.build_graph)",
)


def test_latlon_parsing():
    assert g._try_parse_latlon("48.8674, 2.3636") == (48.8674, 2.3636)
    assert g._try_parse_latlon("48.8674; 2.3636") == (48.8674, 2.3636)
    assert g._try_parse_latlon("not a point") is None


def test_in_paris_bounds():
    assert config.in_paris(*REPUBLIQUE)
    assert config.in_paris(*LUXEMBOURG)
    assert not config.in_paris(*LONDON)


def test_geocode_rejects_out_of_bounds():
    with pytest.raises(RouteError):
        g.geocode_point(f"{LONDON[0]}, {LONDON[1]}")


def test_geocode_empty():
    with pytest.raises(RouteError):
        g.geocode_point("")


def test_speed_model():
    # walk is slower than bike => walking takes longer for the same distance
    assert config.speed_ms("walk") < config.speed_ms("bike")


@graph_available
def test_plain_route_connected():
    graph = g.load_graph()
    route = g.plain_route(graph, *REPUBLIQUE, *LUXEMBOURG, mode="walk")
    assert route.distance_m > 0
    assert route.time_s > 0
    assert len(route.coords) >= 2
    # The straight-line distance is ~2.4 km; a real walk path is longer, not shorter.
    assert route.distance_m >= 2000


@graph_available
def test_bike_faster_than_walk_same_route():
    graph = g.load_graph()
    walk = g.plain_route(graph, *REPUBLIQUE, *LUXEMBOURG, mode="walk")
    bike = g.plain_route(graph, *REPUBLIQUE, *LUXEMBOURG, mode="bike")
    assert bike.time_s < walk.time_s
