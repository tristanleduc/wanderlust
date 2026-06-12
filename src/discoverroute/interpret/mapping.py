"""Bridge the LLM/keyword "brief keys" to the taxonomy's category affinity.

Call 1 (vibe→weights) and the keyword fallback both speak a small, human set of
keys — ``cafe, park, bookshop, museum, bakery, restaurant, bar, viewpoint,
market, historic`` (category keys) plus ``quiet, green, busy`` (modifiers). The
routing engine, however, scores over the 17-category :mod:`taxonomy` vocabulary
via the ``Weights.category_affinity`` dict. This module is the single, dependency
-light translator between the two, so both producers stay consistent.
"""
from __future__ import annotations

from discoverroute import config
from discoverroute.data import taxonomy

# brief category-key -> taxonomy categories it directly expresses interest in.
CATEGORY_KEYS: dict[str, list[str]] = {
    "cafe": ["cafe"],
    "park": ["park_garden"],
    "bookshop": ["bookshop", "library"],
    "museum": ["museum_gallery", "theatre_cinema", "artwork"],
    "bakery": ["bakery_food_shop"],
    "restaurant": ["restaurant"],
    "bar": ["bar_pub"],
    "viewpoint": ["viewpoint", "attraction"],
    "market": ["market", "specialty_shop"],
    "historic": ["monument_historic", "place_of_worship"],
}

# Modifier keys shape every category via its intrinsic priors (not 1:1 to a
# category): green→greenness, quiet→quietness, busy→liveliness (1−quietness).
MODIFIER_KEYS = ("green", "quiet", "busy")

# Inverted: taxonomy category -> the brief category-keys that target it.
_KEYS_FOR_CATEGORY: dict[str, list[str]] = {}
for _key, _cats in CATEGORY_KEYS.items():
    for _c in _cats:
        _KEYS_FOR_CATEGORY.setdefault(_c, []).append(_key)

# All keys a producer is expected to emit (category keys + modifiers).
BRIEF_KEYS: tuple[str, ...] = tuple(CATEGORY_KEYS) + MODIFIER_KEYS


def brief_scores_to_affinity(scores: dict[str, float]) -> dict[str, float]:
    """Map brief-key scores → a floored affinity over every taxonomy category.

    Each category takes the strongest signal among: its direct category-key
    score, and the modifier contributions (green·greenness, quiet·quietness,
    busy·liveliness). The top category is scaled to 1.0 and the rest floored to
    ``AFFINITY_FLOOR`` — the same shape :func:`embed.vibe_to_affinity` returns,
    so the routing engine cannot tell which producer ran.
    """
    green = float(scores.get("green", 0.0) or 0.0)
    quiet = float(scores.get("quiet", 0.0) or 0.0)
    busy = float(scores.get("busy", 0.0) or 0.0)

    raw: dict[str, float] = {}
    for cat in taxonomy.CATEGORIES:
        contribs = [0.0]
        for key in _KEYS_FOR_CATEGORY.get(cat, []):
            contribs.append(float(scores.get(key, 0.0) or 0.0))
        contribs.append(green * taxonomy.greenness(cat))
        contribs.append(quiet * taxonomy.quietness(cat))
        contribs.append(busy * (1.0 - taxonomy.quietness(cat)))
        raw[cat] = max(contribs)

    hi = max(raw.values()) or 1.0
    floor = config.AFFINITY_FLOOR
    return {c: floor + (1.0 - floor) * (v / hi) for c, v in raw.items()}
