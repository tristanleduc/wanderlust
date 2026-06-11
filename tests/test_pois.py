"""Brick 1 tests: taxonomy classification, confidence, corridor selection."""
from __future__ import annotations

import pytest

from discoverroute import config
from discoverroute.data import taxonomy
from discoverroute.routing import graph as g
from discoverroute.routing import pois as poimod

pois_available = pytest.mark.skipif(
    not config.POIS_PATH.exists(),
    reason="POI table not built (run: python -m discoverroute.data.build_pois)",
)
graph_available = pytest.mark.skipif(
    not config.GRAPH_WALK_PATH.exists(), reason="Paris graph not built"
)

REPUBLIQUE = (48.8674, 2.3636)
LUXEMBOURG = (48.8462, 2.3372)


def test_classify_categories():
    assert taxonomy.classify({"leisure": "park"}) == "park_garden"
    assert taxonomy.classify({"amenity": "cafe"}) == "cafe"
    assert taxonomy.classify({"tourism": "viewpoint"}) == "viewpoint"
    assert taxonomy.classify({"historic": "monument"}) == "monument_historic"
    assert taxonomy.classify({"shop": "books"}) == "bookshop"
    assert taxonomy.classify({"amenity": "place_of_worship"}) == "place_of_worship"
    # noise excluded
    assert taxonomy.classify({"amenity": "bank"}) is None
    assert taxonomy.classify({"shop": "supermarket"}) is None
    assert taxonomy.classify({}) is None


def test_confidence_monotonic():
    bare = taxonomy.confidence({"amenity": "cafe"})  # no name even
    named = taxonomy.confidence({"amenity": "cafe", "name": "Le Petit Café"})
    rich = taxonomy.confidence({
        "amenity": "cafe", "name": "Le Petit Café", "wikidata": "Q1",
        "description": "x", "website": "http://x", "opening_hours": "Mo-Su",
    })
    assert 0.0 <= bare < named < rich <= 1.0


def test_feature_priors_in_range():
    for cat in taxonomy.CATEGORIES:
        assert 0.0 <= taxonomy.greenness(cat) <= 1.0
        assert 0.0 <= taxonomy.quietness(cat) <= 1.0
    # park is the greenest category
    greens = {c: taxonomy.greenness(c) for c in taxonomy.CATEGORIES}
    assert max(greens, key=greens.get) == "park_garden"


def test_corridor_width_grows_with_budget():
    assert config.corridor_halfwidth_m(1.0) > config.corridor_halfwidth_m(0.0)


@pois_available
@graph_available
def test_corridor_selection_real():
    graph = g.load_graph()
    route = g.plain_route(graph, *REPUBLIQUE, *LUXEMBOURG, mode="walk")
    narrow = poimod.corridor_pois(route.coords, budget=0.0)
    wide = poimod.corridor_pois(route.coords, budget=1.0)
    assert len(narrow) > 0
    # wider corridor admits at least as many candidates (until the cap)
    assert len(wide) >= len(narrow)
    for p in narrow:
        assert p.category in taxonomy.CATEGORIES
        assert 0.0 <= p.confidence <= 1.0


@pois_available
def test_poi_table_nonempty():
    df = poimod.load_pois()
    assert len(df) > 1000  # Paris has many POIs of interest
    assert set(["category", "greenness", "quietness", "confidence"]).issubset(df.columns)
