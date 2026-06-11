"""Free-text vibe -> category affinity via small-model sentence embeddings.

This is where the nuance lives (spec §9.1): a small CPU text encoder maps the
user's vibe to affinities over the *finite* OSM category vocabulary by cosine
similarity to each category's human-readable gloss. The output is interpretable
weights — the scoring path downstream stays a transparent weighted sum.

Backends (same bge-small model either way):
  1. **fastembed / ONNXRuntime** (preferred) — no torch import. Torch is ~1 GB of
     shared libraries; loading it lazily mid-request froze the app for minutes on
     a memory-pressured laptop and would slow Space cold-starts too.
  2. **sentence-transformers** (fallback) — used only if fastembed is absent.

Everything loads lazily and is cached; gloss embeddings are computed once.
"""
from __future__ import annotations

import functools

import numpy as np

from discoverroute import config
from discoverroute.data import taxonomy


@functools.lru_cache(maxsize=1)
def _encoder():
    """Return (name, encode_fn) where encode_fn(list[str]) -> normalized ndarray."""
    try:
        from fastembed import TextEmbedding

        model = TextEmbedding(model_name=config.EMBED_MODEL)

        def encode(texts: list[str]) -> np.ndarray:
            vecs = np.stack(list(model.embed(texts)))
            return vecs / np.linalg.norm(vecs, axis=1, keepdims=True)

        return "fastembed", encode
    except Exception:  # noqa: BLE001 - fall back to the torch stack
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(config.EMBED_MODEL)

        def encode(texts: list[str]) -> np.ndarray:
            return model.encode(texts, normalize_embeddings=True)

        return "sentence-transformers", encode


@functools.lru_cache(maxsize=1)
def _gloss_matrix():
    """(categories, normalized gloss embedding matrix) computed once."""
    cats = list(taxonomy.CATEGORY_GLOSS.keys())
    glosses = [taxonomy.CATEGORY_GLOSS[c] for c in cats]
    _, encode = _encoder()
    return cats, encode(glosses)


@functools.lru_cache(maxsize=256)
def vibe_to_affinity(vibe: str) -> dict[str, float]:
    """Map a free-text vibe to a {category: affinity in [floor, 1]} dict.

    Cosine similarities are min-max rescaled across categories so the best match
    is 1.0 and the weakest is the configured floor — guaranteeing measurable
    contrast between different vibes while keeping a little exploration room.
    Cached per vibe text (repeated demo prompts don't re-encode).
    """
    vibe = (vibe or "").strip()
    cats, gloss_emb = _gloss_matrix()
    if not vibe:
        return {c: 1.0 for c in cats}  # neutral: equal interest

    _, encode = _encoder()
    q = encode([config.EMBED_QUERY_INSTRUCTION + vibe])[0]
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
