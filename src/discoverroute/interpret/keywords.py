"""Model-free keyword vibe matcher — the always-available safety net.

When Call 1 (the LLM vibe→weights extractor) is unavailable or returns malformed
JSON, this runs instantly with no model: it scans the vibe text for known cues,
unions and averages the matched brief-key weight dicts, and hands the result to
:func:`mapping.brief_scores_to_affinity`. Returns ``None`` when nothing matches,
so the caller can fall through to a neutral (equal-interest) reading.
"""
from __future__ import annotations

from discoverroute.interpret import mapping

# substring cue -> brief-key scores (category keys + quiet/green/busy modifiers).
KEYWORD_WEIGHTS: dict[str, dict[str, float]] = {
    "quiet": {"quiet": 0.9, "busy": 0.1, "park": 0.6},
    "calm": {"quiet": 0.85, "park": 0.5},
    "peace": {"quiet": 0.85, "park": 0.5},
    "coffee": {"cafe": 0.9, "bakery": 0.7},
    "café": {"cafe": 0.9, "bakery": 0.6},
    "cafe": {"cafe": 0.9, "bakery": 0.6},
    "espresso": {"cafe": 0.9},
    "book": {"bookshop": 0.95},
    "librair": {"bookshop": 0.8},  # libraire / librairie
    "read": {"bookshop": 0.7, "quiet": 0.5},
    "green": {"park": 0.9, "green": 0.85},
    "park": {"park": 0.9, "green": 0.8},
    "garden": {"park": 0.9, "green": 0.85},
    "nature": {"park": 0.85, "green": 0.8},
    "water": {"park": 0.6, "viewpoint": 0.6, "green": 0.4},
    "river": {"viewpoint": 0.7, "green": 0.4},
    "canal": {"viewpoint": 0.7, "green": 0.4},
    "histor": {"museum": 0.7, "historic": 0.9},
    "herit": {"historic": 0.9},
    "old": {"historic": 0.7},
    "church": {"historic": 0.8, "quiet": 0.6},
    "museum": {"museum": 0.9, "historic": 0.5},
    "art": {"museum": 0.85},
    "galler": {"museum": 0.85},
    "view": {"viewpoint": 0.9},
    "panoram": {"viewpoint": 0.9},
    "scenic": {"viewpoint": 0.8, "green": 0.5},
    "food": {"restaurant": 0.8, "market": 0.7, "bakery": 0.6},
    "eat": {"restaurant": 0.8, "bakery": 0.5},
    "lunch": {"restaurant": 0.8, "cafe": 0.5},
    "dinner": {"restaurant": 0.85},
    "bakery": {"bakery": 0.9},
    "pastr": {"bakery": 0.9},
    "market": {"market": 0.9},
    "shop": {"market": 0.7},
    "bar": {"bar": 0.85, "busy": 0.5},
    "pub": {"bar": 0.85, "busy": 0.5},
    "drink": {"bar": 0.8},
    "wine": {"bar": 0.8},
    "lively": {"busy": 0.9, "bar": 0.6, "market": 0.6},
    "busy": {"busy": 0.9, "market": 0.6},
    "bustl": {"busy": 0.85, "market": 0.7},
}


def keyword_scores(vibe: str) -> dict[str, float] | None:
    """Union + average the brief-key scores of every cue found in ``vibe``."""
    text = (vibe or "").lower()
    if not text:
        return None
    sums: dict[str, float] = {}
    counts: dict[str, int] = {}
    matched = False
    for cue, weights in KEYWORD_WEIGHTS.items():
        if cue in text:
            matched = True
            for key, val in weights.items():
                sums[key] = sums.get(key, 0.0) + val
                counts[key] = counts.get(key, 0) + 1
    if not matched:
        return None
    return {key: sums[key] / counts[key] for key in sums}


def keyword_affinity(vibe: str) -> dict[str, float] | None:
    """Keyword scores mapped to a taxonomy affinity dict, or ``None``."""
    scores = keyword_scores(vibe)
    if not scores:
        return None
    return mapping.brief_scores_to_affinity(scores)
