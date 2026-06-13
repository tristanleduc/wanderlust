"""Runtime orchestration: turn a user request into routes + map + itinerary.

Brick 3: full discovery routing with manual weights — corridor candidates →
score → shortlist → real travel matrix → orienteering → stitch a single real
polyline, shown against the plain route. Vibe interpretation (Brick 4) and
grounded narration (Brick 6) slot in later behind the same entrypoint.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from discoverroute import config

logger = logging.getLogger("discoverroute")
from discoverroute.routing import area as area_mod
from discoverroute.routing import graph as g
from discoverroute.routing import matrix as mx
from discoverroute.routing import orienteering as ot
from discoverroute.routing import pois as poimod
from discoverroute.routing import scoring
from discoverroute.routing.graph import Route, RouteError


@dataclass
class Alternative:
    """One discovery option (for P1-4 multiple-route presentation)."""
    discovery: Route
    pois: list
    summary_md: str
    itinerary_md: str


@dataclass
class PlanResult:
    plain: Route | None
    discovery: Route | None
    pois: list
    start: tuple[float, float] | None
    end: tuple[float, float] | None
    summary_md: str
    itinerary_md: str
    interpretation_md: str = ""
    alternatives: list = field(default_factory=list)  # incl. the primary, in order
    error: str | None = None


def plan_route(
    start_query: str,
    dest_query: str,
    mode: str = config.DEFAULT_MODE,
    budget: float = config.DEFAULT_BUDGET,
    vibe: str = "",
    adventurousness: float = config.DEFAULT_ADVENTUROUSNESS,
    prefer_green: float = 0.0,
    prefer_quiet: float = 0.0,
    profile: dict | None = None,
    n_alternatives: int = 1,
) -> PlanResult:
    """Plan a route + log one plan-level trace row. Never raises for user errors."""
    result = _plan_route_impl(
        start_query, dest_query, mode, budget, vibe, adventurousness,
        prefer_green, prefer_quiet, profile, n_alternatives,
    )
    try:  # one Open-Trace / Field-Notes row per call; never break a route
        from discoverroute.interpret.affinity import source_of
        from discoverroute.narrate import trace
        trace.log_plan(
            {"start": start_query, "dest": dest_query, "mode": mode,
             "budget": budget, "vibe": vibe, "adventurousness": adventurousness,
             "weights_source": source_of(vibe) if (vibe or "").strip()
             else ("profile" if profile else "manual")},
            {"error": result.error,
             "n_pois_selected": len(result.pois),
             "n_alternatives": len(result.alternatives),
             "plain_min": round(result.plain.time_min, 1) if result.plain else None,
             "discovery_min": (round(result.discovery.time_min, 1)
                               if result.discovery else None)},
        )
    except Exception:  # noqa: BLE001
        pass
    return result


def _plan_route_impl(
    start_query: str,
    dest_query: str,
    mode: str = config.DEFAULT_MODE,
    budget: float = config.DEFAULT_BUDGET,
    vibe: str = "",
    adventurousness: float = config.DEFAULT_ADVENTUROUSNESS,
    prefer_green: float = 0.0,
    prefer_quiet: float = 0.0,
    profile: dict | None = None,
    n_alternatives: int = 1,
) -> PlanResult:
    """Plan a route. Returns a PlanResult; never raises for user-facing errors."""
    # Validate & clamp inputs up front (an unknown mode would silently route at
    # walking speed then mislabel itself; out-of-range budget breaks invariants).
    mode = (mode or "").strip().lower()
    if mode not in config.TRAVEL_SPEEDS_KMH:
        return PlanResult(None, None, [], None, None, "", "",
                          error="Mode must be 'walk' or 'bike'.")
    slider_budget = max(0.0, min(float(budget), config.MAX_BUDGET))
    budget = slider_budget
    adventurousness = max(0.0, min(float(adventurousness), 1.0))
    try:
        start = g.geocode_point(start_query)
        end = g.geocode_point(dest_query)
        # Pick the area: Paris is pre-baked/instant; any other city is fetched
        # live from OSM (only the box spanning the two endpoints).
        area = area_mod.resolve_area(
            start, end, label=_city_label(start_query, dest_query))
        graph = area.graph
        plain = g.plain_route(graph, *start, *end, mode=mode)
    except RouteError as exc:
        return PlanResult(None, None, [], None, None, "", "", error=str(exc))

    # Taste resolution priority: (persistent profile ⊕ trip vibe) > manual sliders.
    from discoverroute.data import taxonomy
    interp_md = ""
    weak_match = False
    exclude_famous = False  # discovery-cue vibes drop well-documented famous sights
    top_requested = None  # the #1 category the vibe asked for (for sparse feedback)
    posture = {c: taxonomy.posture(c) for c in taxonomy.CATEGORIES}
    has_vibe = bool((vibe or "").strip())
    has_profile = bool(
        (profile or {}).get("standing_text", "").strip()
        or (profile or {}).get("saved_categories")
    )
    if has_vibe or has_profile:
        from discoverroute.interpret.profile import effective_weights
        if has_vibe:
            from discoverroute.interpret.vibe import interpret
            interp = interpret(vibe, adventurousness, budget)
            posture = interp.posture
            interp_md = interp.explanation
            weak_match = interp.weak
            adventurousness = interp.adventurousness  # may be cue-boosted (e.g. "hidden gems")
            exclude_famous = interp.exclude_famous
            if not weak_match and interp.top_categories:
                top_requested = interp.top_categories[0]
            # Use the interpreter's OWN affinity (it carries discovery-cue
            # adjustments like zeroing "attraction" for "hidden gems"); blend with
            # the saved profile when present.
            if has_profile:
                weights = effective_weights(profile or {}, trip_affinity=interp.affinity)
                interp_md += "\n\n_Blended with your saved taste profile._"
            else:
                weights = interp.weights
            # An explicit pace word in the vibe ("quick", "all day") nudges the
            # budget — BUT never resurrects a detour the user explicitly disabled
            # by zeroing the slider (P0-3: budget 0 == plain route, slider wins).
            if interp.budget_hint is not None and slider_budget > 0:
                budget = interp.budget_hint
        else:
            weights = effective_weights(profile or {}, "")
            interp_md = _profile_explanation(weights)
    else:
        weights = scoring.manual_weights(prefer_green, prefer_quiet)

    # Budget zero => the result is exactly the plain route (spec P0-3).
    if budget <= 0:
        return PlanResult(
            plain=plain, discovery=None, pois=[], start=start, end=end,
            summary_md=_summary(plain, None, mode),
            itinerary_md="_Detour budget is 0 — this is the plain (fastest) route._",
            interpretation_md=interp_md,
        )

    from discoverroute.narrate.narrate import narrate

    alternatives: list[Alternative] = []
    used_ids: set[int] = set()
    try:
        shortlist, matrix, time_fn = _prepare_discovery(
            graph, start, end, plain, mode, budget, weights, adventurousness,
            posture=posture, exclude_famous=exclude_famous, area=area)
        for _ in range(max(1, n_alternatives)):
            if shortlist is None:
                break
            discovery, selected = _solve_one(
                graph, start, end, plain, mode, budget,
                shortlist, matrix, time_fn, exclude_ids=used_ids, posture=posture)
            if discovery is None or not selected:
                break
            used_ids.update(p.osm_id for p in selected)
            itinerary_md, _ = narrate(
                plain, discovery, selected, vibe=vibe, mode=mode,
                start_label=start_query.strip(), end_label=dest_query.strip(),
                posture=posture, weights=weights, weak=weak_match,
            )
            alternatives.append(Alternative(
                discovery=discovery, pois=selected,
                summary_md=_summary(plain, discovery, mode), itinerary_md=itinerary_md,
            ))
    except Exception as exc:  # noqa: BLE001 - degrade to whatever we have, never crash the UI
        logger.exception("discovery planning failed: %s", exc)
        if not alternatives:  # nothing usable → fall back to the plain route
            return PlanResult(
                plain=plain, discovery=None, pois=[], start=start, end=end,
                summary_md=_summary(plain, None, mode),
                itinerary_md=("_Something went wrong building the detour. Here is the "
                              "plain route; please try again or adjust your inputs._"),
                interpretation_md=interp_md,
            )

    if not alternatives:
        return PlanResult(
            plain=plain, discovery=None, pois=[], start=start, end=end,
            summary_md=_summary(plain, None, mode),
            itinerary_md=(
                "_No worthwhile detour found within your budget. Here is the "
                "near-direct route. Try raising the budget or adventurousness._"
            ),
            interpretation_md=interp_md,
        )

    primary = alternatives[0]
    # Honest feedback when the user's #1 requested category isn't on this corridor
    # (e.g. "jazz and live music" → no music venues between A and B): say so rather
    # than silently labelling churches "a match".
    if top_requested and top_requested not in {p.category for p in primary.pois}:
        nice = taxonomy.pretty_category(top_requested)
        interp_md += (f"\n\n_Heads up: I couldn't find {nice} spots on this stretch — "
                      f"the route shows the nearest things you asked for instead._")

    return PlanResult(
        plain=plain, discovery=primary.discovery, pois=primary.pois,
        start=start, end=end,
        summary_md=primary.summary_md, itinerary_md=primary.itinerary_md,
        interpretation_md=interp_md, alternatives=alternatives,
    )


def _prepare_discovery(graph, start, end, plain, mode, budget, weights, adventurousness,
                       posture=None, exclude_famous=False, area=None):
    """Corridor → score → shortlist → real travel matrix. Done ONCE per request.

    The expensive step is the matrix (cutoff-bounded multi-source Dijkstra), so we
    build it once over the full shortlist and reuse it for every alternative —
    alternatives differ only in which shortlisted POIs the solver may pick.
    Returns (shortlist, matrix, time_fn) or (None, None, None).
    """
    table = area.table if area is not None else None
    origin = area.origin if area is not None else None
    candidates = poimod.corridor_pois(plain.coords, budget, table=table, origin=origin)
    if not candidates:
        return None, None, None
    # Never offer the start or destination itself as a "discovery stop" — a POI
    # sitting on an endpoint (e.g. the square you're starting from) is not a
    # detour and reads as a bug. Drop anything within ENDPOINT_EXCLUSION_M.
    candidates = [p for p in candidates
                  if not _near_endpoint(p.lat, p.lon, start, end)]
    if not candidates:
        return None, None, None
    # Discovery vibes ("hidden gems"): drop famous, well-documented sights so the
    # route stays genuinely off the beaten path (Notre Dame etc. enter via several
    # categories, so filter by tag-richness, not category).
    if exclude_famous:
        kept = [p for p in candidates if p.confidence < config.FAMOUS_CONFIDENCE]
        if kept:
            candidates = kept
    scoring.score_pois(candidates, weights, adventurousness)
    # Open-now awareness: demote places that are closed right now (heavily for
    # stop-at categories, mildly for pass-by; unknown hours left untouched).
    from datetime import datetime

    from discoverroute.routing import hours
    when = datetime.now(area.tz) if area is not None else None
    hours.apply_open_now(candidates, posture, when=when)
    ranked = sorted((p for p in candidates if p.score > 0),
                    key=lambda p: p.score, reverse=True)
    # Dedup within a route: the same OSM place can appear as multiple rows
    # (multipolygon centroids) or two distinct ids can share a name — either way
    # a route must never tell you to visit the same spot twice. Keep first (best).
    seen_id, seen_name, shortlist = set(), set(), []
    for p in ranked:
        nkey = (p.name or "").strip().lower()
        if p.osm_id in seen_id or (nkey and nkey in seen_name):
            continue
        seen_id.add(p.osm_id)
        if nkey:
            seen_name.add(nkey)
        shortlist.append(p)
        if len(shortlist) >= config.SOLVER_CANDIDATES:
            break
    if not shortlist:
        return None, None, None

    points = [start, end] + [(p.lat, p.lon) for p in shortlist]
    cutoff_m = (1.0 + budget) * plain.distance_m
    csr = area.csr if area is not None else None
    matrix = mx.build_matrix(graph, points, mode, cutoff_m, csr=csr)
    return shortlist, matrix, matrix.time_fn()


def _solve_one(graph, start, end, plain, mode, budget, shortlist, matrix, time_fn,
               exclude_ids, posture=None):
    """Solve + stitch one route over the prepared matrix, skipping ``exclude_ids``."""
    pool = [p for p in shortlist if p.osm_id not in exclude_ids]
    if not pool:
        return None, []
    budget_s = (1.0 + budget) * plain.time_s

    # P1-2, single shared pot: a stop's cost = added travel + dwell; a pass-by
    # costs travel only. The solver enforces everything against budget_s, so the
    # total trip (walking + lingering) never exceeds (1+budget) × direct.
    posture_dict = posture or {}

    def posture_fn(poi):
        from discoverroute.data import taxonomy
        poi_category = getattr(poi, "category", "attraction")
        poi_posture = posture_dict.get(poi_category, taxonomy.posture(poi_category))
        if poi_posture == "stop":
            return taxonomy.DWELL_TIME_SEC.get(poi_category, 300.0)
        return 0.0

    result = ot.solve(start, end, pool, budget_s, time_fn,
                      max_pois=config.MAX_DETOUR_STOPS,
                      posture_fn=posture_fn)
    if not result.ordered_pois:
        return None, []
    waypoint_nodes = (
        [matrix.node_for(start)]
        + [matrix.node_for((p.lat, p.lon)) for p in result.ordered_pois]
        + [matrix.node_for(end)]
    )
    discovery = g.stitch_route(graph, waypoint_nodes, mode, result.ordered_pois)
    discovery.dwell_s = result.dwell_time_s
    return discovery, result.ordered_pois


def _near_endpoint(lat: float, lon: float, start, end, thresh_m: float = 80.0) -> bool:
    """True if (lat, lon) is within thresh_m of the start or destination point."""
    import math

    def d(a, b):
        (la1, lo1), (la2, lo2) = a, b
        p1, p2 = math.radians(la1), math.radians(la2)
        dp, dl = math.radians(la2 - la1), math.radians(lo2 - lo1)
        h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        return 2 * 6_371_000.0 * math.asin(math.sqrt(h))
    return d((lat, lon), start) < thresh_m or d((lat, lon), end) < thresh_m


def _city_label(start_query: str, dest_query: str) -> str:
    """A friendly area name for on-demand fetch logs/messages.

    Uses the trailing comma-separated token of an endpoint (often the city), e.g.
    "Tower Bridge, London" → "London". Cosmetic only — never affects routing.
    """
    for q in (dest_query, start_query):
        parts = [p.strip() for p in (q or "").split(",") if p.strip()]
        if len(parts) >= 2:
            return parts[-1]
    return "this area"


def _profile_explanation(weights) -> str:
    top = sorted(weights.category_affinity, key=weights.category_affinity.get,
                 reverse=True)[:4]
    nice = ", ".join(c.replace("_", " ") for c in top)
    return f"**From your saved taste profile** — leaning toward: {nice}."


def _summary(plain: Route, discovery: Route | None, mode: str) -> str:
    line = f"**Plain route** · {plain.distance_m/1000:.2f} km · {plain.time_min:.0f} min"
    if discovery is None:
        return line + f" ({mode})"
    dwell_min = discovery.dwell_s / 60.0
    extra = discovery.time_min + dwell_min - plain.time_min
    dwell_note = f" (incl. ~{dwell_min:.0f} min lingering)" if dwell_min >= 1 else ""
    return (
        f"**Discovery route** · {discovery.distance_m/1000:.2f} km · "
        f"{discovery.time_min + dwell_min:.0f} min · **+{extra:.0f} min** of "
        f"discovery{dwell_note} past {len(discovery.waypoint_pois)} places\n\n"
        f"{line} ({mode}) — shown for comparison"
    )
