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
    try:
        graph = g.load_graph()
        start = g.geocode_point(start_query)
        end = g.geocode_point(dest_query)
        plain = g.plain_route(graph, *start, *end, mode=mode)
    except RouteError as exc:
        return PlanResult(None, None, [], None, None, "", "", error=str(exc))

    # Taste resolution priority: (persistent profile ⊕ trip vibe) > manual sliders.
    from discoverroute.data import taxonomy
    interp_md = ""
    posture = {c: taxonomy.posture(c) for c in taxonomy.CATEGORIES}
    has_vibe = bool((vibe or "").strip())
    has_profile = bool(
        (profile or {}).get("standing_text", "").strip()
        or (profile or {}).get("saved_categories")
    )
    if has_vibe or has_profile:
        from discoverroute.interpret.profile import effective_weights
        weights = effective_weights(profile or {}, vibe)
        if has_vibe:
            from discoverroute.interpret.vibe import interpret
            interp = interpret(vibe, adventurousness, budget)
            posture = interp.posture
            interp_md = interp.explanation
            # An explicit pace word in the vibe ("quick", "all day") overrides the
            # slider — otherwise the shown "pace hint → budget ≈ X" contradicts the
            # route actually planned.
            if interp.budget_hint is not None:
                budget = interp.budget_hint
            if has_profile:
                interp_md += "\n\n_Blended with your saved taste profile._"
        else:
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
            posture=posture)
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
                posture=posture, weights=weights,
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
    return PlanResult(
        plain=plain, discovery=primary.discovery, pois=primary.pois,
        start=start, end=end,
        summary_md=primary.summary_md, itinerary_md=primary.itinerary_md,
        interpretation_md=interp_md, alternatives=alternatives,
    )


def _prepare_discovery(graph, start, end, plain, mode, budget, weights, adventurousness,
                       posture=None):
    """Corridor → score → shortlist → real travel matrix. Done ONCE per request.

    The expensive step is the matrix (cutoff-bounded multi-source Dijkstra), so we
    build it once over the full shortlist and reuse it for every alternative —
    alternatives differ only in which shortlisted POIs the solver may pick.
    Returns (shortlist, matrix, time_fn) or (None, None, None).
    """
    candidates = poimod.corridor_pois(plain.coords, budget)
    if not candidates:
        return None, None, None
    scoring.score_pois(candidates, weights, adventurousness)
    # Open-now awareness: demote places that are closed right now (heavily for
    # stop-at categories, mildly for pass-by; unknown hours left untouched).
    from discoverroute.routing import hours
    hours.apply_open_now(candidates, posture)
    shortlist = sorted((p for p in candidates if p.score > 0),
                       key=lambda p: p.score, reverse=True)[: config.SOLVER_CANDIDATES]
    if not shortlist:
        return None, None, None

    points = [start, end] + [(p.lat, p.lon) for p in shortlist]
    cutoff_m = (1.0 + budget) * plain.distance_m
    matrix = mx.build_matrix(graph, points, mode, cutoff_m)
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
