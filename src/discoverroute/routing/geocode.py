"""Offline geocoding: resolve named Paris places against the cached POI table.

No network. Builds a lazy in-memory index over the ~30k POI names in
``data/paris_pois.parquet`` (normalised: lowercase, accents stripped,
punctuation dropped) and matches queries by exact normalised name first, then
by token containment (every query token must appear in the POI name). Ties are
broken by tag-richness/confidence, so well-documented landmarks win over
sparsely tagged namesakes. Returns ``None`` when not confident — never guesses.
"""
from __future__ import annotations

import functools
import re
import unicodedata
from typing import NamedTuple

# Trailing geography qualifiers we strip from queries ("..., Paris, France").
_TRAILING_TOKENS = ("france", "paris")

# A query must contain at least one token this long to be matchable by token
# containment — otherwise "de la" style fragments would match half the city.
_MIN_SIGNIFICANT_TOKEN = 4


class _Entry(NamedTuple):
    norm: str
    tokens: frozenset[str]
    lat: float
    lon: float
    confidence: float
    n_tags: int
    display: str       # original POI name, for autocomplete suggestions
    category: str


def _normalize(text: str) -> str:
    """Lowercase, strip accents, collapse punctuation/whitespace to spaces."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _strip_trailing_geo(norm: str) -> str:
    """Drop trailing 'paris' / 'france' qualifiers (but never the whole query)."""
    tokens = norm.split()
    while len(tokens) > 1 and tokens[-1] in _TRAILING_TOKENS:
        tokens.pop()
    return " ".join(tokens)


@functools.lru_cache(maxsize=1)
def _index() -> tuple[dict[str, _Entry], list[_Entry]]:
    """Lazy name index: exact normalised-name map + full entry list.

    For duplicate names (e.g. chain shops) the exact map keeps the entry with
    the highest (confidence, n_tags) — the best-documented bearer of the name.
    """
    from discoverroute.routing.pois import load_pois

    df = load_pois()
    named = df[df["name"].notna()]
    exact: dict[str, _Entry] = {}
    entries: list[_Entry] = []
    for row in named.itertuples(index=False):
        norm = _normalize(row.name)
        if not norm:
            continue
        entry = _Entry(
            norm=norm,
            tokens=frozenset(norm.split()),
            lat=float(row.lat),
            lon=float(row.lon),
            confidence=float(row.confidence),
            n_tags=int(row.n_tags),
            display=str(row.name),
            category=str(row.category),
        )
        entries.append(entry)
        best = exact.get(norm)
        if best is None or (entry.confidence, entry.n_tags) > (best.confidence, best.n_tags):
            exact[norm] = entry
    return exact, entries


@functools.lru_cache(maxsize=512)
def local_geocode(query: str) -> tuple[float, float] | None:
    """Resolve a named Paris place to (lat, lon) using only the local POI table.

    Matching order: exact normalised name, then token containment (all query
    tokens present in the POI name), ranked by substring match, confidence,
    tag count, and name brevity. Returns None when nothing matches confidently.
    """
    norm = _strip_trailing_geo(_normalize(query or ""))
    if not norm:
        return None
    exact, entries = _index()

    hit = exact.get(norm)
    if hit is not None:
        return hit.lat, hit.lon

    q_tokens = norm.split()
    if not any(len(t) >= _MIN_SIGNIFICANT_TOKEN for t in q_tokens):
        return None  # only short fragments — too ambiguous to trust
    q_set = frozenset(q_tokens)
    candidates = [e for e in entries if q_set <= e.tokens]
    if not candidates:
        return None
    best = max(
        candidates,
        key=lambda e: (norm in e.norm, e.confidence, e.n_tags, -len(e.norm)),
    )
    return best.lat, best.lon


@functools.lru_cache(maxsize=1024)
def suggest(query: str, limit: int = 8) -> tuple[str, ...]:
    """Autocomplete: Paris place names matching a partial query, best first.

    Matches treat the last token as a prefix (the user is mid-word). Ranked by
    (substring match, confidence, tag richness, name brevity); deduplicated by
    display name. Pure local index — no network. Returns () for short/ambiguous
    input rather than guessing.
    """
    norm = _strip_trailing_geo(_normalize(query or ""))
    if len(norm) < 3:
        return ()
    _, entries = _index()
    toks = norm.split()
    head, last = frozenset(toks[:-1]), toks[-1]

    scored: list[tuple[tuple, _Entry]] = []
    for e in entries:
        if norm in e.norm:
            rank = 2  # full query appears verbatim in the name
        elif head <= e.tokens and any(t.startswith(last) for t in e.tokens):
            rank = 1  # all complete tokens present, last token a prefix
        else:
            continue
        scored.append(((rank, e.confidence, e.n_tags, -len(e.norm)), e))

    scored.sort(key=lambda t: t[0], reverse=True)
    out: list[str] = []
    seen: set[str] = set()
    for _, e in scored:
        if e.display in seen:
            continue
        seen.add(e.display)
        out.append(e.display)
        if len(out) >= limit:
            break
    return tuple(out)
