"""Call 1 — vibe → routing weights via MiniCPM5-1B (JSON-only, lean).

Asks the in-Space 1B model for a small fixed-schema JSON of preference weights,
validates it hard, and maps it onto the taxonomy affinity the router consumes.
Any failure — model absent (off-GPU), invalid JSON, or missing keys — returns
``None`` so the caller falls back to the keyword matcher. Every attempt is
traced (``used_fallback=True`` when the model's output is rejected).
"""
from __future__ import annotations

import functools
import json
import re
import time

from discoverroute.interpret import mapping

# NOTE on prompt design: the previous schema literally showed each key as
# `"cafe": 0.0-1.0`, and the 1B model parroted the `0.0` back as the value —
# returning an all-zero weighting that the router can't act on (a "quiet green
# wander" came out tasteless). We now state the 0..1 meaning in words, forbid the
# all-zero / all-equal degenerate answers explicitly, and give ONE worked example
# (a vibe unrelated to any preset) so the model copies the *shape*, not a value.
SYSTEM_PROMPT = (
    "You convert a walk/ride 'vibe' into place-type preference weights for a "
    "routing engine.\n"
    "For each place type, score how strongly the vibe calls for it: 0 means "
    "irrelevant, 1 means central to the vibe. Most vibes strongly want only two "
    "to four types — give those 0.7-1.0 and keep the rest low. Never set every "
    "value to 0, and never give every type the same value.\n"
    "detour_budget_multiplier is how far off the direct line the vibe justifies: "
    "0.5 = stay direct, 2.0 = big detours welcome.\n"
    "Reply with ONLY a JSON object (no prose, no markdown) using EXACTLY these "
    "keys: cafe, park, bookshop, museum, bakery, restaurant, bar, viewpoint, "
    "market, quiet, green, historic, busy, detour_budget_multiplier.\n"
    "Example — for the vibe \"sunny riverside picnic\":\n"
    '{"cafe":0.4,"park":0.9,"bookshop":0.1,"museum":0.1,"bakery":0.6,'
    '"restaurant":0.2,"bar":0.1,"viewpoint":0.7,"market":0.5,"quiet":0.6,'
    '"green":0.9,"historic":0.2,"busy":0.1,"detour_budget_multiplier":1.2}'
)

REQUIRED_KEYS = (
    "cafe", "park", "bookshop", "museum", "bakery", "restaurant", "bar",
    "viewpoint", "market", "quiet", "green", "historic", "busy",
    "detour_budget_multiplier",
)


def _extract_json(text: str) -> dict | None:
    """Pull the first balanced JSON object out of a model response."""
    if not text:
        return None
    # strip code fences if present
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE)
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except Exception:  # noqa: BLE001
                    return None
    return None


def _validate(obj: dict | None) -> dict | None:
    """Require all keys present and numeric; coerce to floats. Else None."""
    if not isinstance(obj, dict):
        return None
    out: dict[str, float] = {}
    for key in REQUIRED_KEYS:
        if key not in obj:
            return None
        try:
            out[key] = float(obj[key])
        except (TypeError, ValueError):
            return None
    return out


def _is_degenerate(weights: dict[str, float]) -> bool:
    """A weighting carries no usable taste signal if every place-type score is
    zero, or they're all equal (the model emitted a flat default). Such output
    passed ``_validate`` but tells the router nothing — so we reject it and let
    the dispatcher fall through to the embedding tier, which *does* read the vibe.
    (``detour_budget_multiplier`` is excluded — it isn't a place-type score.)"""
    cats = [v for k, v in weights.items() if k != "detour_budget_multiplier"]
    if not cats:
        return True
    if max(cats) <= 0.0:                     # all-zero
        return True
    if max(cats) - min(cats) < 1e-9:         # all-equal → no differentiation
        return True
    return False


@functools.lru_cache(maxsize=256)
def extract(vibe: str) -> dict | None:
    """Return ``{"affinity", "budget_multiplier", "raw"}`` or ``None``.

    ``None`` means "use the fallback": either the model is unavailable
    (off-GPU) or it produced output that failed validation.
    """
    vibe = (vibe or "").strip()
    if not vibe:
        return None

    from discoverroute.narrate import narrate as _narrate  # lazy: llm_available()
    from discoverroute.narrate import trace

    if not _narrate.llm_available():
        return None  # off-GPU: skip straight to the fallback (no trace noise)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Vibe: {vibe}\nReturn the JSON weights now."},
    ]
    t0 = time.time()
    try:
        from discoverroute.narrate.llm import run_inference
        # Reasoning pass: MiniCPM5-1B is hybrid-reasoning, and scoring a fuzzy vibe
        # across 14 types is exactly the kind of short deliberation a 1B does better
        # with than off-the-cuff. enable_thinking=True lets it reason, then emit the
        # JSON; run_inference strips the <think> block and returns only the JSON. The
        # budget covers the reasoning + the ~120-token object (truncated reasoning →
        # empty answer → clean fallback).
        raw_text = run_inference(messages, max_new_tokens=512, enable_thinking=True)
    except Exception as exc:  # noqa: BLE001 - never break interpretation
        latency = int((time.time() - t0) * 1000)
        trace.log_trace("vibe_extraction", {"vibe": vibe},
                        {"error": f"{type(exc).__name__}: {exc}"},
                        latency, used_fallback=True)
        return None

    latency = int((time.time() - t0) * 1000)
    parsed = _validate(_extract_json(raw_text))
    # Reject unparseable OR degenerate (all-zero / all-equal) output: both leave the
    # router with no taste signal, so fall through to the embedding tier instead.
    if parsed is None or _is_degenerate(parsed):
        trace.log_trace("vibe_extraction", {"vibe": vibe},
                        {"raw": raw_text, "degenerate": parsed is not None},
                        latency, used_fallback=True)
        return None

    affinity = mapping.brief_scores_to_affinity(parsed)
    budget_mult = max(0.5, min(2.0, parsed["detour_budget_multiplier"]))
    trace.log_trace("vibe_extraction", {"vibe": vibe}, parsed,
                    latency, used_fallback=False)
    return {"affinity": affinity, "budget_multiplier": budget_mult, "raw": parsed}
