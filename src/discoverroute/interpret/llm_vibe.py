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

SYSTEM_PROMPT = (
    "You are a routing preference extractor.\n"
    "Output ONLY valid JSON. No prose, no explanation, no markdown.\n"
    'Schema: {"cafe": 0.0-1.0, "park": 0.0-1.0, "bookshop": 0.0-1.0, '
    '"museum": 0.0-1.0, "bakery": 0.0-1.0, "restaurant": 0.0-1.0, '
    '"bar": 0.0-1.0, "viewpoint": 0.0-1.0, "market": 0.0-1.0, '
    '"quiet": 0.0-1.0, "green": 0.0-1.0, "historic": 0.0-1.0, '
    '"busy": 0.0-1.0, "detour_budget_multiplier": 0.5-2.0}\n'
    "All keys required. Values reflect how strongly the vibe matches each."
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
        {"role": "user", "content": f"Extract routing weights for this vibe: {vibe}"},
    ]
    t0 = time.time()
    try:
        from discoverroute.narrate.llm import run_inference
        raw_text = run_inference(messages, max_new_tokens=160, temperature=0.2)
    except Exception as exc:  # noqa: BLE001 - never break interpretation
        latency = int((time.time() - t0) * 1000)
        trace.log_trace("vibe_extraction", {"vibe": vibe},
                        {"error": f"{type(exc).__name__}: {exc}"},
                        latency, used_fallback=True)
        return None

    latency = int((time.time() - t0) * 1000)
    parsed = _validate(_extract_json(raw_text))
    if parsed is None:
        trace.log_trace("vibe_extraction", {"vibe": vibe},
                        {"raw": raw_text}, latency, used_fallback=True)
        return None

    affinity = mapping.brief_scores_to_affinity(parsed)
    budget_mult = max(0.5, min(2.0, parsed["detour_budget_multiplier"]))
    trace.log_trace("vibe_extraction", {"vibe": vibe}, parsed,
                    latency, used_fallback=False)
    return {"affinity": affinity, "budget_multiplier": budget_mult, "raw": parsed}
