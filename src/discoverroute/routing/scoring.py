"""POI scoring + submodular set reward.

Scoring is a transparent weighted sum over precomputed POI features (category
affinity, greenness, quietness), modulated by confidence and adventurousness —
fully debuggable, no black box (spec §9.1, §9.2). The set reward is *submodular*:
within a category each additional similar POI is worth less, which is the
structural mechanism that produces diversity (spec §9.2).

Weights are produced manually for Bricks 2-3 (sliders) and by the vibe
interpreter for Brick 4 — same structure either way.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from discoverroute.data import taxonomy

# Each additional POI in the same category is worth this factor more times less:
# ranks contribute score * decay**rank (rank 0 = full). 0.5 => 1, 0.5, 0.25, ...
DIVERSITY_DECAY = 0.5

# Anonymous POIs (no OSM name) are demoted by this factor — applied BEFORE the
# adventurousness serendipity boost, so high adventurousness surfaces *named*
# hidden gems instead of flooding the route with un-findable "a piece of public
# art" entries. (Parks/fountains/art are 40-83% unnamed in OSM.)
UNNAMED_SCORE_FACTOR = 0.45


@dataclass
class Weights:
    """Interpretable scoring weights. category_affinity maps category -> [0,1].

    Greenness/quietness are not separate weight terms: they enter affinity
    directly — folded in by ``manual_weights`` for the sliders, and carried by the
    category glosses for vibe/profile embeddings — so scoring stays a single
    transparent term (affinity) with no always-zero dead weights.
    """

    category_affinity: dict[str, float] = field(default_factory=dict)
    w_category: float = 1.0

    @classmethod
    def uniform(cls, **kw) -> "Weights":
        """Equal affinity for every category (a neutral baseline)."""
        return cls(category_affinity={c: 1.0 for c in taxonomy.CATEGORIES}, **kw)


def manual_weights(prefer_green: float = 0.0, prefer_quiet: float = 0.0,
                   base: float = 0.15) -> Weights:
    """Brick 2-3 manual sliders → per-category affinity.

    The green/quiet sliders are folded directly into each category's affinity via
    its feature priors (plus a small ``base`` so nothing is ever fully excluded),
    so raising "prefer green" actually pulls parks/viewpoints into the route
    rather than being a negligible tilt on a uniform interest. This mirrors how
    Brick 4 will emit category affinity from a free-text vibe (same structure).
    """
    affinity = {
        c: base
        + prefer_green * taxonomy.greenness(c)
        + prefer_quiet * taxonomy.quietness(c)
        for c in taxonomy.CATEGORIES
    }
    return Weights(category_affinity=affinity, w_category=1.0)


def base_score(poi, weights: Weights, adventurousness: float) -> float:
    """Score one POI: weighted feature sum modulated by confidence & adventurousness.

    Two effects of adventurousness (spec §9.4, P1-3):
      1. the confidence penalty fades:  raw * confidence**(1 - adv)
         (adv=0 → low-confidence places heavily penalised; adv=1 → no penalty);
      2. a serendipity *injection* actively boosts under-documented places:
         × (1 + adv * (1 - confidence))
    So low adventurousness sticks to well-known, well-documented spots, while
    high adventurousness deliberately surfaces sparse/hidden-gem POIs.
    """
    affinity = weights.category_affinity.get(poi.category, 0.0)
    raw = weights.w_category * affinity
    if raw <= 0:
        return 0.0
    adv = min(1.0, max(0.0, adventurousness))
    confidence_factor = poi.confidence ** (1.0 - adv)
    serendipity = 1.0 + adv * (1.0 - poi.confidence)
    # Name-aware demotion (adv-independent): only penalise POIs that explicitly
    # carry an empty/None name. POIs with no ``name`` attribute at all (synthetic
    # test objects) are treated as named, so this never perturbs unit tests.
    name_factor = 1.0
    if hasattr(poi, "name"):
        _name = getattr(poi, "name")
        if _name is None or (isinstance(_name, str) and not _name.strip()):
            name_factor = UNNAMED_SCORE_FACTOR
    return raw * name_factor * confidence_factor * serendipity


def score_pois(pois: list, weights: Weights, adventurousness: float) -> list:
    """Assign ``.score`` to each POI in place and return the list."""
    for p in pois:
        p.score = base_score(p, weights, adventurousness)
    return pois


def set_reward(pois: list, decay: float = DIVERSITY_DECAY) -> float:
    """Submodular reward of a *set* of scored POIs (diminishing within category)."""
    by_cat: dict[str, list[float]] = defaultdict(list)
    for p in pois:
        by_cat[p.category].append(p.score)
    total = 0.0
    for scores in by_cat.values():
        for rank, s in enumerate(sorted(scores, reverse=True)):
            total += s * (decay ** rank)
    return total


def _cat_reward(scores: list[float], decay: float) -> float:
    return sum(s * (decay ** rank) for rank, s in enumerate(sorted(scores, reverse=True)))


def marginal_gain(current: list, candidate, decay: float = DIVERSITY_DECAY) -> float:
    """Exact submodular delta of adding ``candidate`` to ``current``.

    Only the candidate's category re-ranks, so we recompute that category's
    contribution before/after — this correctly accounts for lower-scoring
    same-category POIs being demoted (which the naive rank formula misses).
    """
    same = [p.score for p in current if p.category == candidate.category]
    return _cat_reward(same + [candidate.score], decay) - _cat_reward(same, decay)
