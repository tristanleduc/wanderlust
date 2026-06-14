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

# NOTE on prompt design (two parrot traps, both seen live in the traces):
#  1) the original schema showed each key as `"cafe": 0.0-1.0`; the 1B parroted
#     the `0.0` as the value → all-zero weighting → tasteless route.
#  2) replacing it with ONE worked JSON example backfired worse: the model copied
#     the example's numbers VERBATIM regardless of the vibe (a "quiet green wander"
#     came back byte-identical to the "riverside picnic" example).
# Lesson: give the 1B no concrete number-set to copy. State the 0..1 meaning in
# words, teach the *mapping* with short word→type cues (not a full object), and
# forbid the degenerate answers. Wrong/empty output is still caught downstream
# (_is_degenerate → embed tier), so the route is never left tasteless.
SYSTEM_PROMPT = (
    "You convert a walk/ride 'vibe' into place-type preference weights for a "
    "routing engine.\n"
    "For EACH place type listed below, output a number from 0 to 1 for how "
    "strongly THIS vibe calls for it: 0 = irrelevant, ~0.5 = a little, 0.8-1.0 = "
    "central to the vibe. A typical vibe strongly wants only two to four types — "
    "score those high and keep the rest low.\n"
    "Read the actual words of the vibe and score from them, for example: "
    "'green' or 'park' or 'nature' → park and green high; 'quiet' or 'calm' → "
    "quiet high; 'lively' or 'buzzing' → busy and bar high; 'coffee' or 'café' → "
    "cafe high; 'books' → bookshop high; 'history' or 'old' → historic high. "
    "Never make every value 0, and never make every value the same.\n"
    "detour_budget_multiplier: 0.5 = keep it direct, up to 2.0 = big detours "
    "welcome.\n"
    "Output ONLY a JSON object (no prose, no markdown) with EXACTLY these keys, "
    "in this order: cafe, park, bookshop, museum, bakery, restaurant, bar, "
    "viewpoint, market, quiet, green, historic, busy, detour_budget_multiplier."
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
    from discoverroute import config
    think = config.VIBE_THINKING
    meta_in = {"vibe": vibe, "thinking": think}  # mode recorded for the A/B
    t0 = time.time()
    try:
        from discoverroute.narrate.llm import run_inference
        # A/B (config.VIBE_THINKING): with thinking ON, MiniCPM5-1B reasons before
        # emitting JSON — but the <think> block + the ~120-token object need real
        # room, so give it 1024 (512 ran past the budget and returned empty in the
        # first live test). No-think is lean and fast. run_inference strips the
        # <think> block; a truncated/unclosed reasoning → empty answer → fallback.
        budget = 1024 if think else 256
        raw_text = run_inference(messages, max_new_tokens=budget, enable_thinking=think)
    except Exception as exc:  # noqa: BLE001 - never break interpretation
        latency = int((time.time() - t0) * 1000)
        trace.log_trace("vibe_extraction", meta_in,
                        {"error": f"{type(exc).__name__}: {exc}"},
                        latency, used_fallback=True)
        return None

    latency = int((time.time() - t0) * 1000)
    parsed = _validate(_extract_json(raw_text))
    # Reject unparseable OR degenerate (all-zero / all-equal) output: both leave the
    # router with no taste signal, so fall through to the embedding tier instead.
    if parsed is None or _is_degenerate(parsed):
        trace.log_trace("vibe_extraction", meta_in,
                        {"raw": raw_text, "degenerate": parsed is not None},
                        latency, used_fallback=True)
        return None

    affinity = mapping.brief_scores_to_affinity(parsed)
    budget_mult = max(0.5, min(2.0, parsed["detour_budget_multiplier"]))
    trace.log_trace("vibe_extraction", meta_in, parsed,
                    latency, used_fallback=False)
    return {"affinity": affinity, "budget_multiplier": budget_mult, "raw": parsed}
