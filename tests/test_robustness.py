"""Regression tests for the adversarial-review fixes (input robustness + clarity).

These lock in invariants that were previously violated: mode validation, the
budget=0 == plain-route guarantee, non-Paris rejection, nonsense-vibe → neutral,
the unnamed-POI demotion, and place-count consistency across UI surfaces.
"""
from __future__ import annotations

import app
from discoverroute.data import taxonomy
from discoverroute.interpret.affinity import resolve_affinity
from discoverroute.pipeline import plan_route
from discoverroute.routing import scoring

S = "Place de la République, Paris"
D = "Jardin du Luxembourg, Paris"


# ---- input validation ------------------------------------------------------
def test_invalid_mode_rejected():
    assert plan_route(S, D, mode="car").error
    assert plan_route(S, D, mode="xyz").error


def test_uppercase_mode_normalized():
    assert plan_route(S, D, mode="WALK").error is None


def test_far_apart_endpoints_rejected_not_namesake_routed():
    # World support: endpoints on different continents can't form one walkable
    # discovery route. Resolve via lat/lon (no network) so the distance cap fires
    # — and crucially we get an honest error, never a fake namesake route.
    london, tokyo = "51.5079, -0.0877", "35.6586, 139.7454"
    r = plan_route(london, tokyo, vibe="quiet")
    assert r.error and "far" in r.error.lower()
    assert r.discovery is None and not r.pois


def test_budget_zero_is_plain_route_even_with_pace_word():
    # P0-3: an explicit 0 slider must win over a vibe pace hint ("all day").
    r = plan_route(S, D, budget=0.0, vibe="I want to spend all day exploring")
    assert r.discovery is None and not r.pois


# ---- vibe interpretation ---------------------------------------------------
def test_nonsense_vibe_degrades_to_neutral():
    aff, _ = resolve_affinity("quantum physics asdfgh")
    spread = max(aff.values()) - min(aff.values())
    assert spread < 1e-6  # all categories equal → neutral


def test_real_vibe_is_confident():
    aff, _ = resolve_affinity("quiet green park")
    assert (max(aff.values()) - min(aff.values())) > 0.2


# ---- unnamed-POI demotion --------------------------------------------------
class _POI:
    def __init__(self, name, category="park_garden", confidence=0.5):
        self.name, self.category, self.confidence = name, category, confidence


def test_unnamed_poi_scored_below_named():
    w = scoring.Weights(category_affinity={"park_garden": 1.0})
    named = scoring.base_score(_POI("Jardin X"), w, adventurousness=1.0)
    unnamed = scoring.base_score(_POI(None), w, adventurousness=1.0)
    assert unnamed < named  # demoted even at max adventurousness


def test_high_adventurousness_not_mostly_unnamed():
    r = plan_route(S, D, vibe="hidden gems off the beaten path",
                   budget=0.7, adventurousness=1.0)
    if r.pois:
        unnamed = sum(1 for p in r.pois
                      if not (getattr(p, "name", None) and str(p.name).strip()))
        assert unnamed / len(r.pois) <= 0.5


# ---- labels & count consistency --------------------------------------------
def test_display_label_article_and_no_snake_case():
    assert taxonomy.display_label(_POI(None, "artwork")) == "a piece of public art"
    assert taxonomy.display_label(_POI(None, "attraction")) == "a landmark"
    assert "_" not in taxonomy.display_label(_POI(None, "monument_historic"))
    assert taxonomy.display_label(_POI("Louvre")) == "Louvre"


def test_place_count_consistent_across_surfaces():
    r = plan_route(S, D, vibe="quiet green bookshops", budget=0.5, n_alternatives=1)
    if r.alternatives:
        a = r.alternatives[0]
        n = len(a.pois)
        assert f"{n} place" in a.summary_md
        assert f"{n} place" in app._alt_label(0, a, r.plain)
        assert f"{n} place" in a.itinerary_md
