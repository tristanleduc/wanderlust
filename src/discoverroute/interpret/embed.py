"""Free-text vibe -> category affinity via small-model sentence embeddings.

This is where the nuance lives (spec §9.1): a small CPU text encoder maps the
user's vibe to affinities over the *finite* OSM category vocabulary by cosine
similarity to each category's human-readable gloss. The output is interpretable
weights — the scoring path downstream stays a transparent weighted sum.

The model loads lazily so the rest of the app (and the walking skeleton) runs
without it. Category gloss embeddings are computed once and cached.
"""
from __future__ import annotations

import functools

from discoverroute import config
from discoverroute.data import taxonomy


@functools.lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(config.EMBED_MODEL)


@functools.lru_cache(maxsize=1)
def _gloss_matrix():
    """(categories, normalized gloss embedding matrix) computed once."""
    cats = list(taxonomy.CATEGORY_GLOSS.keys())
    glosses = [taxonomy.CATEGORY_GLOSS[c] for c in cats]
    emb = _model().encode(glosses, normalize_embeddings=True)
    return cats, emb


def vibe_to_affinity(vibe: str) -> dict[str, float]:
    """Map a free-text vibe to a {category: affinity in [floor, 1]} dict.

    Cosine similarities are min-max rescaled across categories so the best match
    is 1.0 and the weakest is the configured floor — guaranteeing measurable
    contrast between different vibes while keeping a little exploration room.
    """
    vibe = (vibe or "").strip()
    cats, gloss_emb = _gloss_matrix()
    if not vibe:
        return {c: 1.0 for c in cats}  # neutral: equal interest

    query = config.EMBED_QUERY_INSTRUCTION + vibe
    q = _model().encode([query], normalize_embeddings=True)[0]
    sims = gloss_emb @ q  # cosine (both normalized)

    lo, hi = float(sims.min()), float(sims.max())
    span = hi - lo
    # If the vibe is off-domain (e.g. "I'm hungry on a Tuesday"), the similarities
    # are nearly flat across categories. Don't manufacture confident preferences
    # from noise — treat it as neutral (equal interest) instead.
    if span < config.MIN_AFFINITY_SPAN:
        return {c: 1.0 for c in cats}
    floor = config.AFFINITY_FLOOR
    return {c: floor + (1.0 - floor) * (float(s) - lo) / span for c, s in zip(cats, sims)}
