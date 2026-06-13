"""Persistent taste profile blended with per-trip mood (spec P1-1).

A profile is standing free-text preferences + a bag of saved place categories
(places the user tagged as loved). Effective routing affinity combines the
profile with the current trip's mood:  effective = f(taste, mood).

No accounts: the profile is a single local object persisted per device in the
browser (gr.BrowserState in the UI). This module is pure logic over a plain dict
so it is fully testable without the UI.
"""
from __future__ import annotations

from discoverroute import config
from discoverroute.data import taxonomy
from discoverroute.routing.scoring import Weights

# How much a single saved place in a category lifts that category's affinity,
# saturating so a handful of saves matters but a hundred doesn't dominate.
_SAVED_STEP = 0.5


def empty_profile() -> dict:
    return {"standing_text": "", "saved_categories": []}


def _saved_affinity(saved_categories: list[str]) -> dict[str, float]:
    """Affinity contribution from saved places (count -> saturating boost)."""
    counts: dict[str, int] = {}
    for c in saved_categories or []:
        if c in taxonomy.CATEGORIES:
            counts[c] = counts.get(c, 0) + 1
    out = {c: 0.0 for c in taxonomy.CATEGORIES}
    for c, n in counts.items():
        out[c] = 1.0 - (1.0 / (1.0 + _SAVED_STEP * n))  # 1 save→0.33, 2→0.5, ∞→1
    return out


def profile_affinity(profile: dict) -> dict[str, float] | None:
    """Affinity implied by the profile alone, or None if the profile is empty."""
    profile = profile or {}
    text = (profile.get("standing_text") or "").strip()
    saved = profile.get("saved_categories") or []
    if not text and not saved:
        return None

    from discoverroute.interpret import embed
    base = embed.vibe_to_affinity(text) if text else {c: 0.0 for c in taxonomy.CATEGORIES}
    saved_aff = _saved_affinity(saved)
    # take the stronger signal per category, then floor for a little exploration
    merged = {c: max(base.get(c, 0.0), saved_aff.get(c, 0.0)) for c in taxonomy.CATEGORIES}
    floor = config.AFFINITY_FLOOR
    return {c: floor + (1.0 - floor) * v for c, v in merged.items()}


def effective_weights(profile: dict, trip_vibe: str = "",
                      mood_blend: float = 0.6, trip_affinity=None) -> Weights:
    """Blend persistent taste with the current trip's mood into scoring weights.

    ``mood_blend`` is the weight on the per-trip vibe (0 = profile only,
    1 = mood only). When only one signal exists, it is used directly; when
    neither does, every category is weighted equally (neutral).

    ``trip_affinity`` lets the caller pass the vibe affinity it already computed
    (e.g. the interpreter's, which carries discovery-cue adjustments) instead of
    re-deriving it here — so those adjustments aren't silently dropped.
    """
    prof = profile_affinity(profile)
    trip = trip_affinity
    if trip is None and (trip_vibe or "").strip():
        from discoverroute.interpret.affinity import affinity_only
        trip = affinity_only(trip_vibe)

    if prof is None and trip is None:
        affinity = {c: 1.0 for c in taxonomy.CATEGORIES}
    elif prof is None:
        affinity = trip
    elif trip is None:
        affinity = prof
    else:
        affinity = {
            c: (1 - mood_blend) * prof.get(c, 0.0) + mood_blend * trip.get(c, 0.0)
            for c in taxonomy.CATEGORIES
        }
    return Weights(category_affinity=affinity, w_category=1.0)
