#!/usr/bin/env python
"""Quick test of P1-2 dual budget implementation."""

import math
from discoverroute.routing import orienteering as ot
from discoverroute.routing import scoring
from discoverroute.data import taxonomy


class FakePOI:
    """Minimal POI with identity equality."""
    def __init__(self, lat, lon, category, score):
        self.lat, self.lon, self.category, self.score = lat, lon, category, score


def planar_time(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


START, END = (0.0, 0.0), (10.0, 0.0)


def test_basic_backward_compat():
    """Test that old API (no dual budget) still works."""
    pois = [FakePOI(5, 1.0, "cafe", 5.0), FakePOI(5, 2.0, "park", 5.0)]
    res = ot.solve(START, END, pois, budget_s=10.0, time_fn=planar_time)
    assert res.ordered_pois == []  # direct time is 10, no room for detours
    print("✓ Backward compatibility test passed")


def test_dual_budget_with_posture():
    """Test that dual budget respects both constraints."""
    # Create a café (stop) and a park (pass)
    cafe = FakePOI(5.0, 1.0, "cafe", 10.0)  # high value
    park = FakePOI(5.0, 2.0, "park_garden", 5.0)  # medium value, pass-by

    # Posture function: returns dwell time for stops, 0 for passes
    def posture_fn(poi):
        if poi.category == "cafe":
            return taxonomy.DWELL_TIME_SEC.get("cafe", 600.0)  # ~10 min dwell
        else:
            return 0.0  # park is pass-by

    # Budget: 30 seconds travel + 5 seconds dwell
    res = ot.solve(
        START, END, [cafe, park], budget_s=30.0, time_fn=planar_time,
        dwell_budget_s=5.0, posture_fn=posture_fn
    )

    # Café has 600+ sec dwell which exceeds dwell budget of 5 sec,
    # so it should NOT be selected even though it has high value
    assert len(res.ordered_pois) == 0 or all(p.category != "cafe" for p in res.ordered_pois)
    print("✓ Dual budget constraint test passed")


def test_pass_by_ignores_dwell_budget():
    """Test that pass-by POIs don't consume dwell budget."""
    park1 = FakePOI(3.0, 0.5, "park_garden", 5.0)
    park2 = FakePOI(7.0, 0.5, "park_garden", 5.0)

    def posture_fn(poi):
        return 0.0  # all parks are pass-by

    # With 0 dwell budget, parks should still be selectable
    res = ot.solve(
        START, END, [park1, park2], budget_s=15.0, time_fn=planar_time,
        dwell_budget_s=0.0, posture_fn=posture_fn
    )

    # Both parks should be on the direct line (free) and high value (diverse)
    assert len(res.ordered_pois) > 0
    print("✓ Pass-by ignores dwell budget test passed")


def test_dwell_time_returned():
    """Test that dwell_time_s and detour_distance_m are tracked."""
    cafe = FakePOI(5.0, 1.0, "cafe", 10.0)

    def posture_fn(poi):
        return 600.0 if poi.category == "cafe" else 0.0

    res = ot.solve(
        START, END, [cafe], budget_s=20.0, time_fn=planar_time,
        dwell_budget_s=700.0, posture_fn=posture_fn
    )

    # Result should have dwell_time_s tracked
    assert hasattr(res, 'dwell_time_s')
    assert hasattr(res, 'detour_distance_m')
    print(f"✓ Dwell time tracking test passed (dwell={res.dwell_time_s}s, detour={res.detour_distance_m}m)")


def test_taxonomy_dwell_times():
    """Test that taxonomy has dwell time data."""
    assert hasattr(taxonomy, 'DWELL_TIME_SEC')
    assert "cafe" in taxonomy.DWELL_TIME_SEC
    assert "park_garden" in taxonomy.DWELL_TIME_SEC

    cafe_dwell = taxonomy.dwell_time_sec("cafe")
    assert cafe_dwell > 0  # cafe is a stop

    park_dwell = taxonomy.dwell_time_sec("park_garden")
    assert park_dwell == 0  # park is a pass-by

    print(f"✓ Taxonomy dwell times test passed (cafe={cafe_dwell}s, park={park_dwell}s)")


if __name__ == "__main__":
    test_backward_compat()
    test_taxonomy_dwell_times()
    test_dual_budget_with_posture()
    test_pass_by_ignores_dwell_budget()
    test_dwell_time_returned()
    print("\n✅ All tests passed!")
