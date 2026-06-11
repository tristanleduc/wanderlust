"""Grounded itinerary narration.

Two generators behind one gate:
  * a deterministic **template** — grounded by construction (only ever inserts
    real waypoint names + the start/end labels), the safe default; and
  * an optional **LLM** (Qwen3.5-9B) that adds voice, used only when it runs
    (GPU/Space) and only if its output passes the zero-hallucination gate.

``narrate`` always returns text that passes ``verify_grounded`` — the LLM is a
best-effort enhancer that silently falls back to the template on any violation.
"""
from __future__ import annotations

import os

from discoverroute import config
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


def template_narration(plain, discovery, pois, vibe, mode, start_label="",
                       end_label="", posture=None) -> str:
    posture = posture or {}
    extra = round(discovery.time_min - plain.time_min)
    unit = "minute" if extra == 1 else "minutes"
    lead = f"### Why this route\n"
    vibe_clause = f" for a *{vibe.strip()}*" if (vibe or "").strip() else ""
    lead += (
        f"Spending **{extra} extra {unit}**{vibe_clause}, your {mode} threads "
        f"{len(pois)} discoveries between {start_label or 'the start'} and "
        f"{end_label or 'the destination'}:\n"
    )
    lines = [lead]
    for i, p in enumerate(pois, 1):
        name = p.name or f"a {p.category.replace('_', ' ')}"
        reason = _REASON.get(p.category, "a stop worth making")
        verb = _verb(posture.get(p.category, "pass"))
        lines.append(f"{i}. **{name}** — {verb.lower()} for {reason}.")
    lines.append(
        f"\nThen on to {end_label or 'your destination'}. Every place above is a "
        f"real spot on your route — nothing invented."
    )
    return "\n".join(lines)


def llm_available() -> bool:
    """True only if explicitly enabled and a GPU + transformers are present."""
    if os.environ.get("DISCOVERROUTE_USE_LLM", "auto").lower() in ("0", "false", "off"):
        return False
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except Exception:
        return False
    try:
        import torch
        if os.environ.get("DISCOVERROUTE_USE_LLM", "auto").lower() in ("1", "true", "on"):
            return True
        return bool(torch.cuda.is_available())
    except Exception:
        return False


def narrate(plain, discovery, pois, vibe="", mode="walk", start_label="",
            end_label="", posture=None) -> tuple[str, bool]:
    """Return (markdown, used_llm). Output is guaranteed grounded."""
    template = template_narration(
        plain, discovery, pois, vibe, mode, start_label, end_label, posture
    )
    if not llm_available():
        return template, False

    try:
        text = _llm_narration(plain, discovery, pois, vibe, mode, start_label, end_label)
        ok, offenders = grounding.verify_grounded(text, pois, start_label, end_label)
        if ok and text.strip():
            return text, True
        print(f"[narrate] LLM output rejected by grounding gate; offenders={offenders}",
              flush=True)
    except Exception as exc:  # noqa: BLE001 - never let narration break a route
        print(f"[narrate] LLM failed ({type(exc).__name__}): {exc}", flush=True)
    return template, False  # fail-closed: ship the grounded template


def _llm_narration(plain, discovery, pois, vibe, mode, start_label, end_label) -> str:
    """Generate narration with Qwen3.5-9B, constrained to the allowed names."""
    from discoverroute.narrate.llm import generate

    names = [p.name or f"a {p.category.replace('_', ' ')}" for p in pois]
    bullet = "\n".join(
        f"- {n} ({p.category.replace('_', ' ')})" for n, p in zip(names, pois)
    )
    extra = round(discovery.time_min - plain.time_min)
    prompt = (
        "You are a warm local guide writing a short itinerary for a "
        f"{mode} through Paris from {start_label} to {end_label}.\n"
        f"The traveller's vibe: {vibe or 'open to anything'}.\n"
        f"The route adds {extra} minutes to pass these real places, in order:\n"
        f"{bullet}\n\n"
        "Write 3-5 short sentences. CRITICAL RULES: mention ONLY the place names "
        "listed above, spelled exactly. Do NOT invent or name any other place, "
        "landmark, street, or neighbourhood. If unsure, refer to a place by its "
        "type instead of a name."
    )
    return generate(prompt, max_new_tokens=320)
