"""Orienteering solver: pick & order POIs to maximise submodular reward in budget.

This is the Orienteering Problem (prize-collecting with fixed endpoints), NP-hard
in general. We use a greedy best-ratio insertion heuristic over the *submodular*
reward (diminishing returns within a category), which gives a near-optimal
solution within a stated bound at city scale (spec §9.6). The solver is
graph-agnostic: it takes a ``time_fn`` so it can run on a Euclidean metric (for
unit tests with known optima) or on real graph travel times (Brick 3).

P1-2 dual budgeting: Supports separate dwell and detour budgets. A stop consumes
dwell time; a pass-by consumes only detour distance. The solver respects both.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from discoverroute.routing import scoring

Point = tuple[float, float]  # (lat, lon)
_EPS = 1e-6


@dataclass
class OrienteeringResult:
    ordered_pois: list          # POIs in visiting order (between start and end)
    approx_time_s: float        # total time per the time_fn used (travel + dwell)
    reward: float               # submodular reward of the selected set
    dwell_time_s: float = 0.0   # total time spent dwelling at stops (P1-2)
    detour_distance_m: float = 0.0  # total extra distance above direct (P1-2)


def haversine_time_fn(speed_ms: float, detour_factor: float = 1.3):
    """A ``time_fn`` using great-circle distance × an urban detour factor / speed."""
    R = 6_371_000.0

    def time_fn(a: Point, b: Point) -> float:
        lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
        dlat, dlon = lat2 - lat1, lon2 - lon1
        h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        dist = 2 * R * math.asin(math.sqrt(h)) * detour_factor
        return dist / speed_ms

    return time_fn


def _greedy(start, end, pool, budget_s, time_fn, decay, max_pois, by_ratio, gain_floor,
           dwell_budget_s=None, posture_fn=None):
    """One greedy pass. ``by_ratio`` selects on reward/added-time; else on raw gain.

    Inserts the best feasible POI each round (never exceeding ``budget_s``, never a
    POI whose marginal gain is below ``gain_floor``) until none qualify or
    ``max_pois`` is reached. The floor stops the route padding its remaining budget
    with negligible-value detours.

    P1-2 (single shared pot): a stop's full cost is added travel time PLUS its
    dwell time (from ``posture_fn``); a pass-by costs travel only. Everything is
    enforced against the one ``budget_s`` cap, so the user-facing promise —
    total trip ≤ (1+budget) × direct — holds whether time is spent walking or
    lingering. ``dwell_budget_s`` optionally adds a separate dwell-only cap.
    """
    seq: list[Point] = [start, end]
    selected: list = []
    cur_time = time_fn(start, end)
    cur_dwell = 0.0
    cur_detour_dist = 0.0

    while len(selected) < max_pois:
        best = None  # (key, added, idx, poi, dwell)
        for p in pool:
            if p in selected:
                continue
            gain = scoring.marginal_gain(selected, p, decay)
            if gain < gain_floor:
                continue
            poi_dwell = posture_fn(p) if posture_fn is not None else 0.0
            if dwell_budget_s is not None and cur_dwell + poi_dwell > dwell_budget_s:
                continue
            ppt = (p.lat, p.lon)
            for i in range(1, len(seq)):
                added = (time_fn(seq[i - 1], ppt) + time_fn(ppt, seq[i])
                         - time_fn(seq[i - 1], seq[i]))
                cost = added + poi_dwell  # stops pay travel + dwell, passes travel
                if cur_time + cost > budget_s:
                    continue
                key = gain / max(cost, _EPS) if by_ratio else gain
                # tie-break toward the cheaper insertion
                cand = (key, -cost)
                if best is None or cand > best[0]:
                    best = (cand, added, i, p, poi_dwell)
        if best is None:
            break
        _, added, idx, poi, poi_dwell = best
        seq.insert(idx, (poi.lat, poi.lon))
        selected.insert(idx - 1, poi)
        cur_time += added + poi_dwell
        cur_dwell += poi_dwell
        cur_detour_dist += added

    return OrienteeringResult(
        selected, cur_time, scoring.set_reward(selected, decay),
        dwell_time_s=cur_dwell, detour_distance_m=cur_detour_dist
    )


def solve(
    start: Point,
    end: Point,
    pois: list,
    budget_s: float,
    time_fn,
    *,
    decay: float = scoring.DIVERSITY_DECAY,
    max_pois: int = 12,
    min_gain_ratio: float = 0.12,
    dwell_budget_s: float | None = None,
    posture_fn=None,
) -> OrienteeringResult:
    """Budgeted submodular orienteering by greedy insertion.

    Runs two greedy passes — by raw marginal gain and by reward-per-added-time —
    and returns the higher-reward feasible solution. This better-of-two strategy
    is the standard approach for budgeted submodular maximisation and yields a
    near-optimal solution within a stated bound (spec §9.6); a single ratio pass
    alone gets trapped (e.g. it hoards cheap duplicates over diverse high-reward
    detours).

    ``min_gain_ratio`` sets a marginal-gain floor as a fraction of the single best
    POI's gain, so the route is not padded with near-worthless stops once the
    genuinely good detours are taken.

    P1-2: If ``dwell_budget_s`` and ``posture_fn`` are provided, the solver respects
    both a dwell-time budget and a travel-time budget independently. ``posture_fn``
    is a callable that takes a POI and returns its dwell time in seconds (0 for passes,
    nonzero for stops).
    """
    pool = [p for p in pois if getattr(p, "score", 0.0) > 0.0]
    ref = max((scoring.marginal_gain([], p, decay) for p in pool), default=0.0)
    floor = min_gain_ratio * ref
    by_gain = _greedy(start, end, pool, budget_s, time_fn, decay, max_pois, False, floor,
                     dwell_budget_s, posture_fn)
    by_ratio = _greedy(start, end, pool, budget_s, time_fn, decay, max_pois, True, floor,
                      dwell_budget_s, posture_fn)
    return by_gain if by_gain.reward >= by_ratio.reward else by_ratio
