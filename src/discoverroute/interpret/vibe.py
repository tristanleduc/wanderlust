"""Interpret a free-text vibe + adventurousness into inspectable preferences.

Produces the three things spec P0-5 requires:
  (a) category affinity weights  — from sentence embeddings (embed.py)
  (b) a per-category stop/pass posture — category defaults, shifted by mood cues
  (c) a budget interpretation — a hint read from explicit pace words in the vibe

Affinity is the load-bearing signal for routing; posture and the budget hint are
surfaced for the user and consumed by later bricks (dual-budget solving is P1-2).
Everything here is deterministic and debuggable — no hidden state.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from discoverroute import config
from discoverroute.data import taxonomy
from discoverroute.routing.scoring import Weights

# Mood cues that shift posture globally.
_STOP_CUES = ("crawl", "stop", "sit", "linger", "browse", "taste", "coffee",
              "lunch", "dinner", "drink", "relax", "people-watch", "people watch")
_PASS_CUES = ("ride", "cycle", "bike", "wander", "stroll", "roll", "cruise",
              "pass", "walk through", "loop", "scenic route")

# Pace cues that hint a budget (fraction of direct time to spend on discovery).
_LOW_BUDGET_CUES = ("quick", "short", "direct", "fast", "hurry", "straight")
_HIGH_BUDGET_CUES = ("long", "scenic", "leisurely", "all day", "all-day",
                     "explore", "meander", "take your time", "no rush", "epic")


@dataclass
class Interpretation:
    affinity: dict[str, float]
    weights: Weights
    posture: dict[str, str]
    budget_hint: float | None      # suggested budget, or None if not implied
    explanation: str               # human-readable, inspectable
    top_categories: list[str] = field(default_factory=list)


def _contains(text: str, cues) -> bool:
    return any(cue in text for cue in cues)


def interpret(vibe: str, adventurousness: float = config.DEFAULT_ADVENTUROUSNESS,
              budget: float | None = None) -> Interpretation:
    from discoverroute.interpret import embed  # lazy: avoids loading the model unless used

    text = (vibe or "").strip().lower()
    affinity = embed.vibe_to_affinity(vibe)
    weights = Weights(category_affinity=affinity, w_category=1.0)

    # (b) posture: start from category defaults, then let the mood tilt it.
    base_posture = {c: taxonomy.posture(c) for c in affinity}
    if _contains(text, _STOP_CUES) and not _contains(text, _PASS_CUES):
        posture = {c: "stop" for c in base_posture}
    elif _contains(text, _PASS_CUES) and not _contains(text, _STOP_CUES):
        posture = {c: "pass" for c in base_posture}
    else:
        posture = base_posture

    # (c) budget hint from explicit pace words (slider stays authoritative).
    budget_hint = None
    if _contains(text, _HIGH_BUDGET_CUES):
        budget_hint = 1.0
    elif _contains(text, _LOW_BUDGET_CUES):
        budget_hint = 0.2

    top = sorted(affinity, key=affinity.get, reverse=True)[:4]
    explanation = _explain(vibe, top, affinity, posture, budget_hint)
    return Interpretation(affinity, weights, posture, budget_hint, explanation, top)


def _explain(vibe, top, affinity, posture, budget_hint) -> str:
    if not (vibe or "").strip():
        return "_No vibe given — every kind of place is weighted equally._"
    lines = [f"**Reading “{vibe.strip()}” as:**"]
    for c in top:
        nice = c.replace("_", " ")
        lines.append(f"- {nice} (affinity {affinity[c]:.2f}, "
                     f"{'stop at' if posture[c] == 'stop' else 'pass by'})")
    if budget_hint is not None:
        lines.append(f"- pace hint → budget ≈ {budget_hint:.1f}")
    return "\n".join(lines)
