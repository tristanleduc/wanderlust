"""Brick 2 tests: scoring, submodular reward, and the orienteering solver.

Uses a planar Euclidean ``time_fn`` (treating coords as a flat plane) so optima
are hand-computable and deterministic — no graph required.
"""
from __future__ import annotations

import math

from discoverroute.routing import orienteering as ot
from discoverroute.routing import scoring


class FakePOI:
    """Minimal POI with identity equality (so `p in selected` works)."""

    def __init__(self, lat, lon, category, score):
        self.lat, self.lon, self.category, self.score = lat, lon, category, score


def planar_time(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


START, END = (0.0, 0.0), (10.0, 0.0)  # direct distance = 10


# --- scoring / reward --------------------------------------------------------

def test_submodular_reward_diminishes():
    a = FakePOI(0, 0, "cafe", 1.0)
    b = FakePOI(0, 0, "cafe", 1.0)
    c = FakePOI(0, 0, "park", 1.0)
    # two cafes: 1 + 0.5 = 1.5 ; cafe + park: 1 + 1 = 2.0 (diversity wins)
    assert scoring.set_reward([a, b]) == 1.5
    assert scoring.set_reward([a, c]) == 2.0


def test_marginal_gain_accounts_for_demotion():
    low = FakePOI(0, 0, "cafe", 1.0)
    high = FakePOI(0, 0, "cafe", 10.0)
    # adding the high-scoring cafe demotes the low one (1 -> 0.5): delta = 9.5
    assert scoring.marginal_gain([low], high) == 9.5


# --- solver ------------------------------------------------------------------

def test_budget_zero_gives_no_detour():
    pois = [FakePOI(5, 1.0, "x", 5.0), FakePOI(5, 2.0, "y", 5.0)]
    res = ot.solve(START, END, pois, budget_s=10.0, time_fn=planar_time)
    assert res.ordered_pois == []  # any off-line POI would exceed the direct time


def test_known_optimal_selection():
    # A,B sit on the direct line (free). C is a high-value off-line detour.
    # Hand-computed optimum within budget 15 is {C, one-of-A/B} with reward 13:
    #   {A,B}=6 (cost 0) ; {C}=10 (cost 4.14) ; {A,C}=13 (cost ~4.9, feasible) ;
    #   {A,B,C}=16 needs cost ~5.66 -> infeasible at 15.
    # A pure ratio-greedy grabs the free A,B and gets stuck at reward 6; the
    # better-of-two solver must find the reward-13 optimum.
    A = FakePOI(2.0, 0.0, "a", 3.0)
    B = FakePOI(8.0, 0.0, "b", 3.0)
    C = FakePOI(5.0, 5.0, "c", 10.0)
    res = ot.solve(START, END, [A, B, C], budget_s=15.0, time_fn=planar_time)
    chosen = set(res.ordered_pois)
    assert C in chosen and len(chosen) == 2       # C plus exactly one of A/B
    assert abs(res.reward - 13.0) < 1e-9          # the known optimum
    assert res.approx_time_s <= 15.0 + 1e-9       # budget respected


def test_diversity_preferred_over_repetition():
    cafes = [FakePOI(5, 0.2, "cafe", 1.0) for _ in range(5)]
    park = FakePOI(3, 0.2, "park", 0.95)
    view = FakePOI(7, 0.2, "view", 0.95)
    res = ot.solve(START, END, cafes + [park, view],
                   budget_s=100.0, time_fn=planar_time, max_pois=3)
    cats = [p.category for p in res.ordered_pois]
    assert len(res.ordered_pois) == 3
    assert "park" in cats and "view" in cats       # diversity beat 3 cafes
    assert cats.count("cafe") <= 1


def test_budget_is_never_exceeded():
    pois = [FakePOI(5, d, f"c{d}", 3.0) for d in (0.5, 1.0, 1.5, 2.0, 2.5)]
    res = ot.solve(START, END, pois, budget_s=12.0, time_fn=planar_time)
    assert res.approx_time_s <= 12.0 + 1e-9


# --- Brick 7: adventurousness serendipity (P1-3) ---

def test_adventurousness_injects_low_confidence():
    from discoverroute.routing import scoring

    class P:
        def __init__(self, conf):
            self.category, self.greenness, self.quietness, self.confidence = \
                "cafe", 0.0, 0.0, conf
    w = scoring.Weights(category_affinity={"cafe": 1.0}, w_category=1.0)
    low, high = P(0.1), P(1.0)
    # conservative: well-documented place scores higher than the sparse one
    assert scoring.base_score(low, w, 0.0) < scoring.base_score(high, w, 0.0)
    # adventurous: the under-documented place is boosted above the safe one
    assert scoring.base_score(low, w, 1.0) > scoring.base_score(high, w, 1.0)


# --- P1-2: Dual budget tests ---

def test_backward_compat_no_dual_budget():
    """Test that old API (no dual budget params) still works."""
    pois = [FakePOI(5, 1.0, "cafe", 5.0), FakePOI(5, 2.0, "park", 5.0)]
    res = ot.solve(START, END, pois, budget_s=10.0, time_fn=planar_time)
    assert res.ordered_pois == []  # direct time is 10, no room for detours
    assert hasattr(res, 'dwell_time_s')
    assert hasattr(res, 'detour_distance_m')


def test_dual_budget_respects_dwell_constraint():
    """Test that dwell budget is enforced separately from travel budget."""
    # Create high-value café (stop, expensive dwell) and cheap park (pass)
    cafe = FakePOI(5.0, 1.0, "cafe", 10.0)
    park = FakePOI(5.0, 2.0, "park_garden", 3.0)

    def posture_fn(poi):
        # Café: 600 sec dwell; park: 0 sec (pass-by)
        return 600.0 if poi.category == "cafe" else 0.0

    # Travel budget: 30 sec (enough for a detour)
    # Dwell budget: 5 sec (NOT enough for café's 600 sec)
    # → café should be rejected despite high value
    res = ot.solve(
        START, END, [cafe, park], budget_s=30.0, time_fn=planar_time,
        dwell_budget_s=5.0, posture_fn=posture_fn
    )

    # Café should NOT be selected (exceeds dwell budget)
    cafe_selected = any(p.category == "cafe" for p in res.ordered_pois)
    assert not cafe_selected, "Café should not be selected (exceeds dwell budget)"


def test_pass_by_unaffected_by_dwell_budget():
    """Test that pass-by POIs bypass the dwell budget constraint."""
    park1 = FakePOI(3.0, 0.5, "park_garden", 5.0)
    park2 = FakePOI(7.0, 0.5, "park_garden", 5.0)

    def posture_fn(poi):
        # All parks are pass-by (0 dwell)
        return 0.0

    # Zero dwell budget should not prevent parks from being selected
    res = ot.solve(
        START, END, [park1, park2], budget_s=15.0, time_fn=planar_time,
        dwell_budget_s=0.0, posture_fn=posture_fn
    )

    # Should select parks since they don't consume dwell budget
    assert len(res.ordered_pois) > 0


def test_dwell_tracking():
    """Test that dwell_time_s and detour_distance_m are returned."""
    cafe = FakePOI(5.0, 1.0, "cafe", 10.0)

    def posture_fn(poi):
        return 600.0 if poi.category == "cafe" else 0.0

    # Generous budgets to allow selection
    res = ot.solve(
        START, END, [cafe], budget_s=20.0, time_fn=planar_time,
        dwell_budget_s=700.0, posture_fn=posture_fn
    )

    assert hasattr(res, 'dwell_time_s')
    assert hasattr(res, 'detour_distance_m')
    # If café was selected, dwell should reflect its cost
    if any(p.category == "cafe" for p in res.ordered_pois):
        assert res.dwell_time_s > 0
