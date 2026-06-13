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

# Phrasing per category for the template. Generic (no external facts) so the only
# proper noun is the POI's own name -> grounded by construction.
_REASON = {
    "park_garden": "a breath of green to slow down in",
    "water_feature": "a bit of water and calm",
    "viewpoint": "a view worth the pause",
    "monument_historic": "a piece of the city's history",
    "museum_gallery": "art and ideas just off your path",
    "artwork": "a splash of public art",
    "place_of_worship": "a quiet, still interior",
    "library": "a hush of books",
    "bookshop": "shelves worth a browse",
    "theatre_cinema": "a little drama on the way",
    "cafe": "a coffee-stop pause",
    "bakery_food_shop": "something good to eat",
    "restaurant": "a proper bite",
    "bar_pub": "a lively drink",
    "market": "stalls and bustle",
    "specialty_shop": "a characterful find",
    "attraction": "a notable stop",
}


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
                       end_label="", posture=None, weights=None) -> str:
    posture = posture or {}
    n = len(pois)
    extra = round(discovery.time_min + getattr(discovery, "dwell_s", 0.0) / 60.0
                  - plain.time_min)
    unit = "minute" if extra == 1 else "minutes"
    place_word = "place" if n == 1 else "places"
    v = (vibe or "").strip()
    vibe_clause = f" to match your *{v}* mood" if v else ""
    lead = "### Why this route\n"
    lead += (
        f"Spending **{extra} extra {unit}**{vibe_clause}, your {mode} threads "
        f"**{n} {place_word}** between {start_label or 'the start'} and "
        f"{end_label or 'the destination'}:\n"
    )
    # The categories the vibe leans on most — used to tie a stop back to the vibe.
    top_cats: set[str] = set()
    aff = getattr(weights, "category_affinity", None)
    if v and aff:
        top_cats = set(sorted(aff, key=aff.get, reverse=True)[:3])

    lines = [lead]
    prev_cat = None
    for i, p in enumerate(pois, 1):
        label = taxonomy.display_label(p)
        if p.category == prev_cat:  # avoid 3 identical reason lines in a row
            reason = f"another {taxonomy.pretty_category(p.category)} along the way"
        else:
            reason = _REASON.get(p.category, "a spot worth a look")
        prev_cat = p.category
        verb = _verb(posture.get(p.category, "pass"))
        tie = " — a match for your vibe" if (v and p.category in top_cats) else ""
        badge = _hours_badge(p, posture.get(p.category, "pass"))
        lines.append(f"{i}. **{label}** — {verb.lower()} for {reason}{tie}.{badge}")
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
            end_label="", posture=None, weights=None) -> tuple[str, bool]:
    """Return (markdown, used_llm). Output is guaranteed grounded."""
    template = template_narration(
        plain, discovery, pois, vibe, mode, start_label, end_label, posture, weights
    )
    if not llm_available():
        return template, False

    import time

    from discoverroute.narrate import trace

    meta = {"vibe": vibe, "mode": mode, "n_stops": len(pois)}
    t0 = time.time()
    try:
        text = _llm_narration(plain, discovery, pois, vibe, mode,
                              start_label, end_label, weights)
        ok, offenders = grounding.verify_grounded(text, pois, start_label, end_label)
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
                   weights=None) -> str:
    """Generate narration with MiniCPM5-1B, constrained to the allowed names."""
    from discoverroute.narrate.llm import run_inference

    names = [taxonomy.display_label(p) for p in pois]
    bullet = "\n".join(
        f"- {n} ({p.category.replace('_', ' ')})" for n, p in zip(names, pois)
    )
    extra = round(discovery.time_min - plain.time_min)
    total_min = round(discovery.time_min + getattr(discovery, "dwell_s", 0.0) / 60.0)
    weights_line = _weights_summary(weights)

    system = (
        "You are a Parisian city guide who knows every street. Write a warm, "
        "specific, first-person itinerary for this walking route. Reference the "
        "user's stated vibe directly. For each stop, explain in one sentence why "
        "it matches what they were looking for. Format as markdown with one "
        "header per stop.\n"
        "CRITICAL: mention ONLY the place names listed in the prompt, spelled "
        "exactly. Never invent or name any other place, street, landmark, or "
        "neighbourhood. If unsure, refer to a place by its type, not a name."
    )
    user = (
        f"Vibe: {vibe or 'open to anything'}\n"
        + (f"Weights extracted: {weights_line}\n" if weights_line else "")
        + f"Mode: {mode} from {start_label or 'the start'} to "
        f"{end_label or 'the destination'}\n"
        f"Ordered stops:\n{bullet}\n"
        f"Total time: {total_min} minutes (about {extra} minutes of discovery)\n\n"
        "Write the itinerary."
    )
    messages = [{"role": "system", "content": system},
                {"role": "user", "content": user}]
    return run_inference(messages, max_new_tokens=600)
