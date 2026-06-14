"""The zero-hallucination gate (spec P0-6).

A narration is *grounded* iff every place name it mentions exists in the allowed
set (the selected waypoint POIs, plus the start, destination and "Paris"). The
verifier is **fail-closed**: any capitalized place-name-like span it cannot match
to an allowed name counts as a violation, so brittle/creative model output is
rejected rather than risked. Callers fall back to the template (grounded by
construction) on any failure — the released narration always passes.
"""
from __future__ import annotations

import re
import unicodedata

# Lowercase connectors/articles that may appear *inside* a multi-word place name.
# Deliberately excludes list-joiners ("and"/"et") — those connect separate names,
# not parts of one, and would glue distinct places into a single false mention.
_CONNECTORS = {
    "de", "des", "du", "la", "le", "les", "l", "d", "en", "à", "au", "aux",
    "sur", "sous", "of",
}

# Capitalized words that are NOT place names (sentence starters, pronouns, common
# nouns the template/model may capitalize). Compared case-insensitively.
_COMMON = {
    "the", "a", "an", "you", "your", "we", "our", "i", "this", "that", "then",
    "next", "first", "finally", "along", "from", "to", "at", "on", "in", "near",
    "starting", "start", "begin", "head", "continue", "arrive", "end", "route",
    "discovery", "plain", "detour", "walk", "walking", "bike", "biking", "ride",
    "way", "trip", "journey", "minutes", "min", "km", "stop", "pass", "by",
    "past", "via", "and", "but", "with", "for", "as", "it", "its", "after",
    "before", "here", "there", "now", "your", "let", "take", "enjoy", "pause",
    "north", "south", "east", "west", "left", "right", "monday", "today",
    "paris", "parisian",
    # template/narration sentence-starters and connective words
    "why", "spending", "every", "threads", "discoveries", "real", "spot",
    "nothing", "invented", "breath", "hush", "shelves", "stalls", "something",
    "view", "art", "coffee", "drama", "splash", "piece", "bit", "characterful",
    "proper", "lively", "quiet", "notable", "green", "good", "still", "worth",
    # common prose verbs/adverbs that may start a sentence (never place names)
    "stroll", "strolling", "wander", "wandering", "onward", "onwards", "through",
    "some", "heading", "continue", "continuing", "follow", "following", "turn",
    "cross", "crossing", "reach", "reaching", "arriving", "savour", "savor",
    "soak", "grab", "catch", "look", "see", "find", "wind", "winding", "weave",
    "weaving", "dip", "duck", "swing", "loop", "breathe", "slow", "set", "make",
    "expect", "stay", "keep", "give", "spend", "spent", "thread", "threaded",
    "minute", "hour", "hours", "place", "places", "stops", "option", "options",
    # city-independent descriptive words a guide uses: era/architecture styles,
    # nationalities, and generic geographic nouns. Never standalone venue names,
    # so admitting them lets prose breathe without opening a hallucination vector
    # (a distinctive token like "Eiffel" still has to match an allowed name).
    "roman", "gothic", "medieval", "renaissance", "baroque", "romanesque",
    "neoclassical", "art", "deco", "nouveau", "modern", "ancient", "classical",
    "victorian", "georgian", "haussmann", "french", "parisian", "english",
    "british", "spanish", "catalan", "american", "european",
    "river", "riverside", "quarter", "district", "neighbourhood", "neighborhood",
    "bank", "island", "hill", "boulevard", "avenue", "street", "lane", "square",
    "park", "garden", "gardens", "bridge", "quay", "embankment", "canal",
    "market", "quartier", "rue", "pont", "jardin", "plaza", "passeig",
}

_TOKEN_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ0-9'’.\-]*")


def _norm(s: str) -> str:
    """Casefold + strip accents/punctuation for forgiving comparison."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^\w\s]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def allowed_names(pois, start_label: str = "", end_label: str = "",
                  extra_allowed=None) -> list[str]:
    names = [p.name for p in pois if getattr(p, "name", None)]
    for lbl in (start_label, end_label):
        if lbl and lbl.strip():
            names.append(lbl.strip())
    # Geographic context the narrator may name (districts, river, landmarks) —
    # supplied per city by narrate.gazetteer. Real OSM-scale places, not invented
    # venues, so admitting them keeps the grounding guarantee while letting the
    # LLM write like an actual city guide instead of falling back to the template.
    if extra_allowed:
        names.extend(a for a in extra_allowed if a and a.strip())
    names.append("Paris")
    return names


def extract_mentions(text: str) -> list[str]:
    """Return capitalized place-name-like spans (multi-word phrases included).

    Punctuation is a hard break: commas, periods, parentheses etc. end a span, so
    "République, Paris and Jardin du Luxembourg" yields three candidates, not one
    glued phrase.
    """
    # Split on anything that isn't a word char, space, apostrophe or hyphen, so
    # clause/sentence boundaries don't get merged into a name.
    segments = re.split(r"[^\w\s'’\-]+", text)
    mentions: list[str] = []
    for segment in segments:
        mentions.extend(_segment_mentions(segment))
    return mentions


def _segment_mentions(text: str) -> list[str]:
    tokens = [(m.group(0), m.start()) for m in _TOKEN_RE.finditer(text)]
    mentions: list[str] = []
    i, n = 0, len(tokens)
    while i < n:
        word = tokens[i][0]
        if word[:1].isupper() and word.lower() not in _CONNECTORS:
            span = [word]
            j = i + 1
            last_cap = 0
            while j < n:
                w = tokens[j][0]
                if w[:1].isupper() and w.lower() not in _CONNECTORS:
                    span.append(w)
                    last_cap = len(span) - 1
                    j += 1
                elif w.lower() in _CONNECTORS:
                    # skip a run of connectors ("de la", "of the") if an
                    # uppercase name follows; otherwise the span ends here
                    k = j
                    while k < n and tokens[k][0].lower() in _CONNECTORS:
                        k += 1
                    if (k < n and tokens[k][0][:1].isupper()
                            and tokens[k][0].lower() not in _CONNECTORS):
                        span.extend(tokens[t][0] for t in range(j, k))
                        j = k
                    else:
                        break
                else:
                    break
            span = span[: last_cap + 1]
            mentions.append(" ".join(span))
            i = j
        else:
            i += 1
    return mentions


def _is_grounded_mention(mention: str, allowed_norm: list[str]) -> bool:
    toks = _norm(mention).split()
    # Strip leading/trailing common words so a sentence-starter glued to a real
    # place ("From Bastille") reduces to its place core ("Bastille").
    while toks and toks[0] in _COMMON:
        toks.pop(0)
    while toks and toks[-1] in _COMMON:
        toks.pop()
    if not toks:  # nothing but common words -> not a place name
        return True
    core = " ".join(toks)
    # Grounded iff the core is (a substring of) an allowed name. We do NOT accept
    # the reverse (an allowed name being a substring of a longer mention): that is
    # the hallucination vector — appending an invented qualifier to a real name,
    # e.g. "Café de la Paix" -> "Café de la Paix sur Seine".
    return any(core in a for a in allowed_norm if a)


def verify_grounded(text: str, pois, start_label="", end_label="",
                    extra_allowed=None) -> tuple[bool, list[str]]:
    """(ok, offenders). ok=True iff every mention maps to an allowed name.

    ``extra_allowed`` is the per-city geographic gazetteer (districts, river,
    landmarks) the narrator may reference beyond the selected POIs + endpoints.
    """
    allowed_norm = [_norm(a)
                    for a in allowed_names(pois, start_label, end_label, extra_allowed)]
    offenders = [
        mention for mention in extract_mentions(text)
        if not _is_grounded_mention(mention, allowed_norm)
    ]
    return (len(offenders) == 0, offenders)
