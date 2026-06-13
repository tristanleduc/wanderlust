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
    city: str          # "paris" or a pre-baked city slug — for disambiguation


def _normalize(text: str) -> str:
    """Lowercase, strip accents, collapse punctuation/whitespace to spaces."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _strip_trailing_geo(norm: str) -> str:
    """Drop trailing 'paris' / 'france' qualifiers (but never the whole query)."""
    return _split_geo(norm)[0]


@functools.lru_cache(maxsize=1)
def _geo_hints() -> dict[str, str]:
    """Normalised city/qualifier word -> city slug (for trailing-token hints)."""
    from discoverroute import config

    hints = {"paris": "paris", "france": "paris"}
    for slug, spec in config.CITIES.items():
        hints[slug] = slug
        for tok in _normalize(spec["label"]).split():
            hints[tok] = slug
    return hints


def _split_geo(norm: str) -> tuple[str, str | None]:
    """Split a normalised query into (core, city_hint_slug).

    Pops trailing geography qualifiers ("…, london", "…, paris, france") and
    returns which city they point at, so a landmark that exists in two cities can
    be disambiguated by the city the user named.
    """
    tokens = norm.split()
    hints = _geo_hints()
    hint = None
    while len(tokens) > 1 and tokens[-1] in hints:
        hint = hints[tokens[-1]]
        tokens.pop()
    return " ".join(tokens), hint


# Obvious non-Paris places that would otherwise namesake-match a Paris POI
# (e.g. a restaurant literally named "Tokyo"), silently producing a fake route.
# Checked before name matching so they fail with an honest "Paris only" message.
WORLD_PLACES = frozenset({
    "london", "tokyo", "new york", "newyork", "berlin", "rome", "madrid",
    "barcelona", "amsterdam", "brussels", "lisbon", "vienna", "prague",
    "budapest", "moscow", "beijing", "shanghai", "hong kong", "seoul",
    "bangkok", "singapore", "sydney", "melbourne", "dubai", "mumbai", "delhi",
    "new delhi", "cairo", "istanbul", "athens", "dublin", "edinburgh",
    "manchester", "los angeles", "san francisco", "chicago", "boston", "miami",
    "toronto", "montreal", "mexico city", "rio de janeiro", "sao paulo",
    "buenos aires", "kyoto", "osaka", "milan", "venice", "florence", "naples",
    "munich", "frankfurt", "hamburg", "zurich", "geneva", "oslo", "stockholm",
    "copenhagen", "helsinki", "warsaw", "kyiv", "kiev",
    "china", "japan", "america", "usa", "england", "germany", "italy", "spain",
    "russia", "india", "europe", "france",
})


def is_world_place(query: str) -> bool:
    """True if the query is plainly a non-Paris city/country (denylist)."""
    return _strip_trailing_geo(_normalize(query or "")) in WORLD_PLACES


@functools.lru_cache(maxsize=1)
def _index() -> tuple[dict[str, _Entry], list[_Entry]]:
    """Lazy name index over Paris + every pre-baked city's POI names.

    Exact normalised-name map + full entry list. For duplicate names the exact
    map keeps the entry with the highest (confidence, n_tags); the per-entry city
    tag lets a city-hinted query ("…, London") prefer the right city.
    """
    import pandas as pd

    from discoverroute import config
    from discoverroute.routing import area as area_mod
    from discoverroute.routing.pois import load_pois

    sources = [("paris", load_pois())]
    for slug in area_mod.available_cities():
        try:
            sources.append((slug, pd.read_parquet(config.city_pois_path(slug))))
        except Exception:  # noqa: BLE001 - a missing/partial city is non-fatal
            continue

    exact: dict[str, _Entry] = {}
    entries: list[_Entry] = []
    for city, df in sources:
        named = df[df["name"].notna()]
        for row in named.itertuples(index=False):
            norm = _normalize(row.name)
            if not norm:
                continue
            entry = _Entry(
                norm=norm, tokens=frozenset(norm.split()),
                lat=float(row.lat), lon=float(row.lon),
                confidence=float(row.confidence), n_tags=int(row.n_tags),
                display=str(row.name), category=str(row.category), city=city,
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
    norm, hint = _split_geo(_normalize(query or ""))
    if not norm:
        return None
    exact, entries = _index()

    # Exact name match — prefer the hinted city when the query named one.
    if hint:
        for e in entries:
            if e.norm == norm and e.city == hint:
                return e.lat, e.lon
    hit = exact.get(norm)
    if hit is not None:
        return hit.lat, hit.lon

    q_tokens = norm.split()
    if not any(len(t) >= _MIN_SIGNIFICANT_TOKEN for t in q_tokens):
        return None  # only short fragments — too ambiguous to trust
    q_set = frozenset(q_tokens)
    candidates = [e for e in entries if q_set <= e.tokens]
    if hint:
        hinted = [e for e in candidates if e.city == hint]
        if hinted:
            candidates = hinted
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
    norm, hint = _split_geo(_normalize(query or ""))
    if len(norm) < 3:
        return ()
    _, entries = _index()
    if hint:
        entries = [e for e in entries if e.city == hint] or entries
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
