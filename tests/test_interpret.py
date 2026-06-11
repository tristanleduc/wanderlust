"""Brick 4 tests: vibe -> preferences and prompt sensitivity (P0-5).

The embedding model is downloaded on first run; tests are skipped if it (or the
data) is unavailable so the suite still runs in a minimal environment.
"""
from __future__ import annotations

import pytest

from discoverroute import config

st = pytest.importorskip("sentence_transformers")

data_ready = pytest.mark.skipif(
    not (config.GRAPH_WALK_PATH.exists() and config.POIS_PATH.exists()),
    reason="Graph or POI table not built",
)


def test_contrasting_vibes_differ():
    from discoverroute.interpret.vibe import interpret
    green = interpret("quiet green wander")
    lively = interpret("lively café crawl and bar hopping")
    # the top category should differ, and green should rank parks above bars
    assert green.top_categories[0] != lively.top_categories[0]
    assert green.affinity["park_garden"] > green.affinity["bar_pub"]
    assert lively.affinity["bar_pub"] > lively.affinity["park_garden"]


def test_affinity_in_range_and_floored():
    from discoverroute.interpret.vibe import interpret
    r = interpret("museums and historic monuments")
    assert all(config.AFFINITY_FLOOR - 1e-6 <= a <= 1.0 + 1e-6
               for a in r.affinity.values())
    assert max(r.affinity.values()) == pytest.approx(1.0)


def test_empty_vibe_is_neutral():
    from discoverroute.interpret.vibe import interpret
    r = interpret("")
    assert set(r.affinity.values()) == {1.0}


def test_budget_and_posture_hints():
    from discoverroute.interpret.vibe import interpret
    quick = interpret("quick direct ride")
    long = interpret("long scenic meander, no rush")
    assert quick.budget_hint is not None and quick.budget_hint < 0.5
    assert long.budget_hint is not None and long.budget_hint > 0.5
    # "ride" is a pass cue -> everything becomes pass-by
    assert set(quick.posture.values()) == {"pass"}


@data_ready
def test_vibe_changes_route_categories():
    """Same A/B, contrasting vibes -> each route serves ITS OWN vibe best (P0-5).

    Property-based rather than exact category counts (which are brittle across
    embedder backends): scoring each route's categories under a vibe's affinity,
    the route planned FOR that vibe must fit it at least as well as the route
    planned for the contrasting vibe.
    """
    from discoverroute.interpret.embed import vibe_to_affinity
    from discoverroute.pipeline import plan_route

    a = "Place de la République, Paris"
    b = "Jardin du Luxembourg, Paris"
    v_green, v_lively = "quiet green park wander", "lively bar and café crawl"
    green = plan_route(a, b, budget=0.7, vibe=v_green)
    lively = plan_route(a, b, budget=0.7, vibe=v_lively)
    assert green.pois and lively.pois

    # the two routes should not select an identical set of waypoints
    assert {p.osm_id for p in green.pois} != {p.osm_id for p in lively.pois}

    def fit(route, affinity):  # mean affinity of the route's categories
        return sum(affinity.get(p.category, 0.0) for p in route.pois) / len(route.pois)

    aff_green, aff_lively = vibe_to_affinity(v_green), vibe_to_affinity(v_lively)
    assert fit(green, aff_green) >= fit(lively, aff_green)
    assert fit(lively, aff_lively) >= fit(green, aff_lively)
