"""Grounded itinerary narration.

Two generators behind one gate:
  * a deterministic **template** — grounded by construction (only ever inserts
    real waypoint names + the start/end labels), the safe default; and
  * an optional **LLM** (MiniCPM5-1B) that adds voice, used only when it runs
    (GPU/Space) and only if its output passes the zero-hallucination gate.

``narrate`` always returns text that passes ``verify_grounded`` — the LLM is a
best-effort enhancer that silently falls back to the template on any violation.
"""
from __future__ import annotations

import os

from discoverroute.data import taxonomy
from discoverroute.narrate import grounding

# Phrasing per category for the template. Several variants each so a route with
# three parks doesn't read the same line three times — the only proper noun is
# still the POI's own name, so it stays grounded by construction.
_REASONS = {
    "park_garden": ["a breath of green to slow down in",
                    "a pocket of green to catch your breath",
                    "leaves and quiet just off the pavement",
                    "a green pause from the noise"],
    "water_feature": ["a bit of water and calm", "the cool of moving water",
                      "a glassy, still moment"],
    "viewpoint": ["a view worth the pause", "the city opening up below you",
                  "a long look across the rooftops"],
    "monument_historic": ["a piece of the city's history",
                          "a marker of the past hiding in plain sight",
                          "old stone with a story"],
    "museum_gallery": ["art and ideas just off your path", "a room of art to wander",
                       "a quick dose of culture"],
    "artwork": ["a splash of public art", "an unexpected splash of colour",
                "street art worth a glance"],
    "place_of_worship": ["a quiet, still interior", "a hush behind heavy doors",
                         "cool stone and coloured light"],
    "library": ["a hush of books", "shelves and silence", "a reader's pause"],
    "bookshop": ["shelves worth a browse", "a browse you'll lose time in",
                 "stacks to get lost in"],
    "theatre_cinema": ["a little drama on the way", "the glow of a marquee",
                       "a stage-door moment"],
    "cafe": ["a coffee-stop pause", "a caffeine pit-stop",
             "a window seat and a flat white"],
    "bakery_food_shop": ["something good to eat", "a warm-from-the-oven detour",
                         "a snack worth the smell"],
    "restaurant": ["a proper bite", "a table worth sitting down for",
                   "a real meal mid-route"],
    "bar_pub": ["a lively drink", "a round before you carry on",
                "a stool and a cold one"],
    "market": ["stalls and bustle", "noise, colour and haggling", "a market's churn"],
    "specialty_shop": ["a characterful find", "an oddball little shop",
                       "something you didn't know you wanted"],
    "attraction": ["a notable stop", "a landmark worth the look",
                   "an only-here kind of place"],
}

# One evocative word per category, for composing a route title.
_TITLE_WORD = {
    "park_garden": "green", "water_feature": "waterside", "viewpoint": "scenic",
    "monument_historic": "storied", "museum_gallery": "arty", "artwork": "arty",
    "place_of_worship": "quiet", "library": "bookish", "bookshop": "bookish",
    "theatre_cinema": "dramatic", "cafe": "caffeinated", "bakery_food_shop": "tasty",
    "restaurant": "tasty", "bar_pub": "lively", "market": "bustling",
    "specialty_shop": "quirky", "attraction": "landmark",
}


def _reason_for(category: str, occurrence: int) -> str:
    """Pick a reason variant, rotating by how many times this category appeared."""
    variants = _REASONS.get(category)
    if not variants:
        return "a spot worth a look"
    return variants[occurrence % len(variants)]


def _route_title(pois, mode, city_label="") -> str:
    """A short, evocative, grounded headline for the whole walk (no venue names)."""
    from collections import Counter
    counts = Counter(p.category for p in pois)
    words: list[str] = []
    for cat, _ in counts.most_common():
        w = _TITLE_WORD.get(cat)
        if w and w not in words:
            words.append(w)
        if len(words) == 2:
            break
    glyph = "🚲" if mode == "bike" else "🥾"
    mood = " & ".join(words) if words else "discovery"
    where = f" through {city_label}" if city_label else ""
    return f"{glyph} A {mood} {mode}{where}"


def _verb(posture: str) -> str:
    return "Pause at" if posture == "stop" else "Pass by"


def _hours_badge(poi, posture_val: str) -> str:
    """Honest open/closed badge. Unknown hours are flagged only for places you'd
    enter (stops); a park you stroll past needs no 'hours unverified' caveat."""
    state = getattr(poi, "open_state", None)  # OSM opening_hours, when decidable
    if state is True:
        return " · 🟢 open now"
    if state is False:
        return " · 🔴 closed right now"
    if posture_val == "stop":
        return " · ⚪ hours unverified"
    return ""


def template_narration(plain, discovery, pois, vibe, mode, start_label="",
                       end_label="", posture=None, weights=None, weak=False,
                       city_label="") -> str:
    posture = posture or {}
    n = len(pois)
    extra = round(discovery.time_min + getattr(discovery, "dwell_s", 0.0) / 60.0
                  - plain.time_min)
    unit = "minute" if extra == 1 else "minutes"
    place_word = "place" if n == 1 else "places"
    v = (vibe or "").strip()
    # Honest framing for a weak / out-of-vocabulary vibe: don't pretend these are
    # tailored matches (the review found "brutalist architecture" → churches
    # confidently labelled "a match for your vibe").
    if v and weak:
        vibe_clause = (f" — I didn't find a strong match for *{v}*, so here's a "
                       f"varied walk worth taking")
    else:
        vibe_clause = f" to match your *{v}* mood" if v else ""
    title = _route_title(pois, mode, city_label)
    lead = f"### {title}\n"
    lead += (
        f"Spending **{extra} extra {unit}**{vibe_clause}, your {mode} threads "
        f"**{n} {place_word}** between {start_label or 'the start'} and "
        f"{end_label or 'the destination'}:\n"
    )
    # NOTE: we deliberately do NOT tag stops "a match for your vibe". Adversarial
    # review showed that claim overreaches whenever a route backfills with a
    # lower-ranked category (a bakery on a wine vibe, a church on a jazz vibe) —
    # the affinity model can't guarantee per-stop relevance, so the blanket claim
    # reads as a lie. Each stop's own reason text conveys its appeal honestly; the
    # interpretation panel already shows how the vibe was read.
    lines = [lead]
    seen: dict[str, int] = {}  # rotate reason variants per category
    for i, p in enumerate(pois, 1):
        label = taxonomy.display_label(p)
        occ = seen.get(p.category, 0)
        seen[p.category] = occ + 1
        reason = _reason_for(p.category, occ)
        verb = _verb(posture.get(p.category, "pass"))
        badge = _hours_badge(p, posture.get(p.category, "pass"))
        lines.append(f"{i}. **{label}** — {verb.lower()} for {reason}.{badge}")
    lines.append(
        f"\nThen on to {end_label or 'your destination'}. Every place above is a "
        f"real spot on your route — nothing invented."
    )
    return "\n".join(lines)


def llm_available() -> bool:
    """True when the generative narrator (MiniCPM5-1B) should run.

    ZeroGPU gotcha: on a ZeroGPU Space the GPU is allocated on demand *inside* an
    ``@spaces.GPU`` call, so ``torch.cuda.is_available()`` is False here at gate
    time — gating on it would silently force the template forever. We instead
    trust the ZeroGPU/Space environment (and an explicit override). The narrator
    still fails closed to the template if the model errors or fails grounding.
    """
    flag = os.environ.get("DISCOVERROUTE_USE_LLM", "auto").lower()
    if flag in ("0", "false", "off"):
        return False
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except Exception:
        return False
    if flag in ("1", "true", "on"):
        return True
    # ZeroGPU Space: CUDA isn't visible outside @spaces.GPU — enable by environment.
    if os.environ.get("SPACES_ZERO_GPU") or os.environ.get("SPACES_ZERO_GPU_V2"):
        return True
    try:
        import torch
        return bool(torch.cuda.is_available())
    except Exception:
        return False


def narrate(plain, discovery, pois, vibe="", mode="walk", start_label="",
            end_label="", posture=None, weights=None, weak=False,
            geo_allowed=None, city_label="") -> tuple[str, bool]:
    """Return (markdown, used_llm). Output is guaranteed grounded.

    ``geo_allowed`` is the per-city geographic gazetteer (districts, river,
    landmarks) the LLM may name; ``city_label`` localises the guide's voice
    (e.g. "London" instead of the old hardcoded "Parisian").
    """
    template = template_narration(
        plain, discovery, pois, vibe, mode, start_label, end_label, posture, weights,
        weak, city_label
    )
    if not llm_available():
        return template, False

    import time

    from discoverroute.narrate import trace

    meta = {"vibe": vibe, "mode": mode, "n_stops": len(pois)}
    t0 = time.time()
    try:
        text = _llm_narration(plain, discovery, pois, vibe, mode,
                              start_label, end_label, weights, geo_allowed, city_label)
        ok, offenders = grounding.verify_grounded(
            text, pois, start_label, end_label, extra_allowed=geo_allowed)
        latency = int((time.time() - t0) * 1000)
        if ok and text.strip():
            trace.log_trace("narration", meta, {"text": text}, latency,
                            used_fallback=False)
            return text, True
        trace.log_trace("narration", meta, {"text": text, "offenders": offenders},
                        latency, used_fallback=True)
        print(f"[narrate] LLM output rejected by grounding gate; offenders={offenders}",
              flush=True)
    except Exception as exc:  # noqa: BLE001 - never let narration break a route
        trace.log_trace("narration", meta, {"error": f"{type(exc).__name__}: {exc}"},
                        int((time.time() - t0) * 1000), used_fallback=True)
        print(f"[narrate] LLM failed ({type(exc).__name__}): {exc}", flush=True)
    return template, False  # fail-closed: ship the grounded template


def _weights_summary(weights) -> str:
    """Compact 'cafe 0.9, park 0.7' line from the extracted weights, if any."""
    aff = getattr(weights, "category_affinity", None)
    if not aff:
        return ""
    top = sorted(aff, key=aff.get, reverse=True)[:5]
    return ", ".join(f"{c.replace('_', ' ')} {aff[c]:.2f}" for c in top)


def _llm_narration(plain, discovery, pois, vibe, mode, start_label, end_label,
                   weights=None, geo_allowed=None, city_label="") -> str:
    """Generate narration with MiniCPM5-1B, constrained to the allowed names.

    The model may colour the route with the listed neighbourhoods / river /
    landmarks (``geo_allowed``) so it reads like a real guide — but it still must
    not invent a *venue* to visit. Anything it slips past that rule is caught by
    the grounding gate and the template ships instead.
    """
    from discoverroute.narrate.llm import run_inference

    names = [taxonomy.display_label(p) for p in pois]
    bullet = "\n".join(
        f"- {n} ({p.category.replace('_', ' ')})" for n, p in zip(names, pois)
    )
    extra = round(discovery.time_min - plain.time_min)
    total_min = round(discovery.time_min + getattr(discovery, "dwell_s", 0.0) / 60.0)
    weights_line = _weights_summary(weights)
    guide = f"{city_label} " if city_label else ""
    context_terms = ", ".join(geo_allowed) if geo_allowed else ""

    system = (
        f"You are a {guide}local — a sharp, warm city guide who actually walks these "
        "streets. Write a short, vivid, first-person itinerary for this route. Make "
        "it FLOW like a story, not a checklist: open with a one-line evocative title "
        "(as a markdown `### ` heading), then carry the reader from start to finish in "
        "a few short paragraphs, weaving the stops in with sensory detail and natural "
        "transitions ('a block on', 'just around the corner', 'as the street opens up'). "
        "Reference the user's vibe in your own words. Bold each real stop's name the "
        "first time it appears.\n"
        "Set the scene freely with the districts, river, and landmarks under 'You may "
        "reference' — name them to give the walk a sense of place, mention the time of "
        "day or the light, describe what a place feels like. Have a voice.\n"
        "ONE hard rule, and only one: do not invent a *named venue to visit* — every "
        "place you tell the reader to actually stop at or pass must be one of the "
        "'Ordered stops' (spelled close to the list) or the start/destination. You "
        "don't need a name for every sentence; describe freely, just never fabricate a "
        "specific café/shop/museum name that isn't on the list."
    )
    user = (
        f"Vibe: {vibe or 'open to anything'}\n"
        + (f"Weights extracted: {weights_line}\n" if weights_line else "")
        + f"Mode: {mode} from {start_label or 'the start'} to "
        f"{end_label or 'the destination'}\n"
        + (f"You may reference (scene-setting, name freely): {context_terms}\n"
           if context_terms else "")
        + f"Ordered stops (the only venues to route through, in order):\n{bullet}\n"
        f"Total time: {total_min} minutes (about {extra} minutes of discovery)\n\n"
        "Write the titled, flowing itinerary."
    )
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": user}]
    # ≤480 tokens comfortably covers ~6 stops (one short paragraph each) and keeps
    # generation inside the 45s ZeroGPU slice (see llm.GPU_DURATION_S).
    return run_inference(messages, max_new_tokens=480)
