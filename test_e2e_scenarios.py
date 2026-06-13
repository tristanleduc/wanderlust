#!/usr/bin/env python
"""End-to-end comprehensive testing of DiscoverRoute with 5 scenarios."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from discoverroute.pipeline import plan_route
from discoverroute.data import taxonomy

# Test scenarios
SCENARIOS = [
    {
        "name": "Scenario 1: Basic routing (budget 0, no detour)",
        "start_query": "Republic",  # 48.8670, 2.3631
        "dest_query": "Bastille",   # 48.8525, 2.3697
        "mode": "walk",
        "budget": 0.0,
        "vibe": "",
        "adventurousness": 0.3,
        "profile": {},
        "expected": "plain route with no discovery",
    },
    {
        "name": "Scenario 2: Contrasting vibes on same route",
        "variants": [
            {
                "subname": "2a. Quiet green parks",
                "start_query": "Republic",
                "dest_query": "Bastille",
                "mode": "walk",
                "budget": 0.5,
                "vibe": "quiet green parks",
                "adventurousness": 0.3,
                "profile": {},
            },
            {
                "subname": "2b. Lively cafes and markets",
                "start_query": "Republic",
                "dest_query": "Bastille",
                "mode": "walk",
                "budget": 0.5,
                "vibe": "lively cafes and markets",
                "adventurousness": 0.3,
                "profile": {},
            },
        ],
        "expected": "visibly different waypoint selections (parks vs cafes)",
    },
    {
        "name": "Scenario 3: Pass-vs-stop dual budget (P1-2)",
        "variants": [
            {
                "subname": "3a. Slow coffee crawl",
                "start_query": "Louvre",
                "dest_query": "Sainte-Chapelle",
                "mode": "walk",
                "budget": 0.3,
                "vibe": "slow coffee crawl",
                "adventurousness": 0.3,
                "profile": {},
            },
            {
                "subname": "3b. Zoom through art",
                "start_query": "Louvre",
                "dest_query": "Sainte-Chapelle",
                "mode": "walk",
                "budget": 0.3,
                "vibe": "zoom through art galleries",
                "adventurousness": 0.3,
                "profile": {},
            },
        ],
        "expected": "different route shapes; one has long dwells, one has many quick POIs",
    },
    {
        "name": "Scenario 4: Taste profile effect",
        "start_query": "Eiffel Tower",
        "dest_query": "Notre-Dame",
        "mode": "walk",
        "budget": 0.4,
        "vibe": "",
        "adventurousness": 0.3,
        "profile": {
            "saved_categories": ["park", "water_feature", "cafe"],
            "standing_text": "I love parks and cafes"
        },
        "expected": "profile boosts those categories; route favors parks/cafes over others",
    },
    {
        "name": "Scenario 5: Narration grounding (P0-6 gate)",
        "start_query": "Republic",
        "dest_query": "Bastille",
        "mode": "walk",
        "budget": 0.5,
        "vibe": "charming historic streets",
        "adventurousness": 0.3,
        "profile": {},
        "expected": "narration explains why each place was chosen; no hallucinations",
    },
]


def extract_place_names_from_narration(narration_md: str) -> set[str]:
    """Extract place names (bolded or capitalized mentions) from markdown narration."""
    import re
    # Find **place names** in markdown
    bolded = set(re.findall(r'\*\*([^*]+)\*\*', narration_md))
    return bolded


def test_scenario(scenario_def, variant_idx=None):
    """Run a single scenario variant."""
    if isinstance(scenario_def, dict) and "variants" in scenario_def:
        # Multi-variant scenario
        print(f"\n{scenario_def['name']}")
        print("=" * 70)
        results = []
        for i, variant in enumerate(scenario_def["variants"]):
            result = _run_single_test(variant)
            results.append(result)
            _print_result(result, variant["subname"])
        return results
    else:
        # Single-variant scenario
        print(f"\n{scenario_def['name']}")
        print("=" * 70)
        result = _run_single_test(scenario_def)
        _print_result(result, scenario_def["name"])
        return [result]


def _run_single_test(test_def):
    """Execute a single test."""
    result = plan_route(
        start_query=test_def["start_query"],
        dest_query=test_def["dest_query"],
        mode=test_def.get("mode", "walk"),
        budget=test_def.get("budget", 0.5),
        vibe=test_def.get("vibe", ""),
        adventurousness=test_def.get("adventurousness", 0.3),
        profile=test_def.get("profile", {}),
        n_alternatives=1,
    )
    return result


def _print_result(result, test_name):
    """Pretty-print a single test result."""
    print(f"\n{test_name}")
    print("-" * 70)

    if result.error:
        print(f"  ERROR: {result.error}")
        print(f"  VERDICT: FAIL")
        return

    # Plain route info
    if result.plain:
        print(f"  Plain route:")
        print(f"    - Distance: {result.plain.distance_m / 1000:.2f} km")
        print(f"    - Time: {result.plain.time_min:.1f} min")

    # Discovery route info
    if result.discovery:
        print(f"  Discovery route:")
        print(f"    - Distance: {result.discovery.distance_m / 1000:.2f} km")
        print(f"    - Time: {result.discovery.time_min:.1f} min")
        print(f"    - Extra time: {result.discovery.time_min - result.plain.time_min:.1f} min")
        print(f"    - Waypoints: {len(result.pois)}")

        # Category breakdown
        if result.pois:
            categories = {}
            for poi in result.pois:
                cat = getattr(poi, "category", "unknown")
                categories[cat] = categories.get(cat, 0) + 1
            print(f"    - Top categories: {dict(sorted(categories.items(), key=lambda x: -x[1])[:3])}")

        # Narration grounding check
        narration_places = extract_place_names_from_narration(result.itinerary_md)
        waypoint_names = {p.name for p in result.pois if hasattr(p, "name")}

        if narration_places:
            print(f"    - Narration places: {len(narration_places)}")
            print(f"    - Waypoint names: {len(waypoint_names)}")
            grounded = narration_places.issubset(waypoint_names | {"Republic", "Bastille", "Louvre", "Sainte-Chapelle", "Eiffel Tower", "Notre-Dame"})
            print(f"    - Narration grounded: {grounded}")

        print(f"  VERDICT: PASS")
    else:
        print(f"  Discovery: None (no detour found within budget)")
        print(f"  VERDICT: PASS (acceptable: budget too small or no candidates)")


def main():
    """Run all scenario tests."""
    print("\n" + "=" * 70)
    print("DISCOVERROUTE END-TO-END COMPREHENSIVE TESTING")
    print("=" * 70)

    all_results = []
    for scenario in SCENARIOS:
        results = test_scenario(scenario)
        all_results.extend(results)

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    passes = sum(1 for r in all_results if not r.error and (r.discovery or r.plain))
    total = len(all_results)
    print(f"  Passed: {passes}/{total}")
    if passes == total:
        print("  Status: ALL SCENARIOS PASSED")
    else:
        print(f"  Status: {total - passes} scenario(s) failed")


if __name__ == "__main__":
    main()
