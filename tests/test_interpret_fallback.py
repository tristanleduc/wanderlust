"""Fallback vibe-interpretation: keyword matcher, brief→taxonomy mapping, JSON parse.

These cover the model-free path that runs whenever the LLM (Call 1) is absent or
returns malformed output — the path actually exercised off-GPU.
"""
from __future__ import annotations

from discoverroute.data import taxonomy
from discoverroute.interpret import affinity, keywords, llm_vibe, mapping


def _is_floored_affinity(aff: dict) -> bool:
    return (set(aff) == set(taxonomy.CATEGORIES)
            and all(0.0 <= v <= 1.0 for v in aff.values())
            and abs(max(aff.values()) - 1.0) < 1e-9)


def test_keyword_affinity_matches_books_and_green():
    aff = keywords.keyword_affinity("quiet green bookshops")
    assert aff is not None and _is_floored_affinity(aff)
    # the bookish/green categories should outrank a lively bar
    assert aff["bookshop"] > aff["bar_pub"]
    assert aff["park_garden"] > aff["bar_pub"]


def test_keyword_affinity_none_when_no_cue():
    assert keywords.keyword_affinity("zzzz qwerty") is None
    assert keywords.keyword_scores("") is None


def test_brief_scores_to_affinity_shape_and_modifiers():
    # a pure "green" modifier should lift the greenest category to the top
    aff = mapping.brief_scores_to_affinity({"green": 1.0})
    assert _is_floored_affinity(aff)
    assert aff["park_garden"] >= max(aff[c] for c in taxonomy.CATEGORIES)


def test_llm_json_extract_and_validate():
    good = ('{"cafe":0.9,"park":0.1,"bookshop":0.2,"museum":0.3,"bakery":0.4,'
            '"restaurant":0.5,"bar":0.6,"viewpoint":0.7,"market":0.8,"quiet":0.2,'
            '"green":0.3,"historic":0.4,"busy":0.5,"detour_budget_multiplier":1.4}')
    obj = llm_vibe._validate(llm_vibe._extract_json("noise " + good + " trailing"))
    assert obj is not None and obj["cafe"] == 0.9
    # missing a required key -> rejected
    assert llm_vibe._validate(llm_vibe._extract_json('{"cafe":0.9}')) is None
    # not JSON at all -> None
    assert llm_vibe._extract_json("sorry, I cannot do that") is None


def test_llm_rejects_degenerate_weights():
    """All-zero / all-equal extractions pass _validate but carry no taste signal,
    so _is_degenerate must flag them (the live trace showed a real all-zero row for
    'quiet green wander' that the router then ignored)."""
    keys = llm_vibe.REQUIRED_KEYS
    all_zero = {k: 0.0 for k in keys}
    all_zero["detour_budget_multiplier"] = 0.5
    assert llm_vibe._is_degenerate(all_zero) is True
    all_equal = {k: 0.5 for k in keys}
    all_equal["detour_budget_multiplier"] = 1.0
    assert llm_vibe._is_degenerate(all_equal) is True
    # a real, differentiated weighting is kept
    good = {k: 0.1 for k in keys}
    good.update(park=0.9, green=0.9, quiet=0.7, detour_budget_multiplier=1.2)
    assert llm_vibe._is_degenerate(good) is False


def test_resolve_affinity_neutral_on_empty():
    aff, src = affinity.resolve_affinity("")
    assert src == "neutral"
    assert all(abs(v - 1.0) < 1e-9 for v in aff.values())


def test_resolve_affinity_returns_full_taxonomy():
    aff, src = affinity.resolve_affinity("lively cafe crawl")
    assert set(aff) == set(taxonomy.CATEGORIES)
    assert src in {"llm", "embed", "keyword"}
