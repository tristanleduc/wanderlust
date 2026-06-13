"""Resolve a free-text vibe into category affinity, with graceful fallbacks.

Single entry point for "vibe → affinity over the taxonomy". Tiers, best first:

  1. MiniCPM5-1B Call 1 (``llm_vibe.extract``) — when a GPU is present in-Space.
  2. bge-small embeddings (``embed.vibe_to_affinity``) — CPU, no model download
     beyond the small encoder; the strictly-better-than-keywords middle tier.
  3. Keyword matcher (``keywords.keyword_affinity``) — instant, model-free net.
  4. Neutral — equal interest in everything.

Every tier returns the same floored ``{category: affinity}`` shape, so the
routing engine (and the ``Weights`` struct) is oblivious to which one ran.
"""
from __future__ import annotations

import functools

from discoverroute import config
from discoverroute.data import taxonomy


def _neutral() -> dict[str, float]:
    return {c: 1.0 for c in taxonomy.CATEGORIES}


def _cap_top_n(aff: dict[str, float]) -> dict[str, float]:
    """Zero all but the top-N categories so the long tail can't backfill routes
    with off-vibe filler. (Embed self-caps; this also covers the LLM/keyword
    tiers so the guarantee holds regardless of which one ran.)"""
    if not aff:
        return aff
    keep = set(sorted(aff, key=aff.get, reverse=True)[: config.TOP_AFFINITY_CATEGORIES])
    return {c: (v if c in keep else 0.0) for c, v in aff.items()}


@functools.lru_cache(maxsize=256)
def resolve_affinity(vibe: str) -> tuple[dict[str, float], str]:
    """Return ``(affinity, source)`` where source ∈ {llm, embed, keyword, neutral}."""
    vibe = (vibe or "").strip()
    if not vibe:
        return _neutral(), "neutral"

    # tier 1 — LLM extraction (in-Space GPU only)
    from discoverroute.interpret import llm_vibe
    result = llm_vibe.extract(vibe)
    if result:
        return _cap_top_n(result["affinity"]), "llm"

    # tier 2 — sentence embeddings (CPU); embed.vibe_to_affinity self-caps
    try:
        from discoverroute.interpret import embed
        return embed.vibe_to_affinity(vibe), "embed"
    except Exception:  # noqa: BLE001 - encoder unavailable → keyword net
        pass

    # tier 3 — keyword matcher (model-free)
    from discoverroute.interpret import keywords
    kw = keywords.keyword_affinity(vibe)
    if kw:
        return _cap_top_n(kw), "keyword"

    return _neutral(), "neutral"


def affinity_only(vibe: str) -> dict[str, float]:
    return resolve_affinity(vibe)[0]


def source_of(vibe: str) -> str:
    return resolve_affinity(vibe)[1]
