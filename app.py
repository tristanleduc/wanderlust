"""DiscoverRoute — gradio.Server entrypoint (Hugging Face Space app_file).

Off-Brand custom frontend: instead of Gradio's default column layout, this serves
a hand-built app-shell (ui/shell.py) from ``app.get("/")`` and exposes the planner
as ``@app.api`` endpoints called from the browser via ``@gradio/client`` (the
required path for ZeroGPU).

Run locally:  python app.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# The package lives in src/ and is not pip-installed on the Space container —
# put it on the path before any discoverroute import (also makes plain
# `python app.py` work locally without PYTHONPATH).
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from fastapi.responses import HTMLResponse
from gradio import Server

# ZeroGPU scans for @spaces.GPU functions AT STARTUP — import the module that
# defines one (cheap: model/torch loading stays lazy inside the function).
import discoverroute.narrate.llm  # noqa: F401  (registers spaces.GPU)

from discoverroute.pipeline import plan_route
from discoverroute.ui import map as mapui
from discoverroute.ui import shell

N_ALTERNATIVES = 3

app = Server()


def _alt_label(i: int, alt, plain) -> str:
    extra = round(alt.discovery.time_min + alt.discovery.dwell_s / 60.0 - plain.time_min)
    from collections import Counter
    top = Counter(p.category for p in alt.pois).most_common(2)
    flavor = ", ".join(c.replace("_", " ") for c, _ in top)
    n = len(alt.pois)
    return (f"Option {i + 1} · {alt.discovery.distance_m / 1000:.1f} km · +{extra} min · "
            f"{n} place{'' if n == 1 else 's'} ({flavor})")


@app.api(name="suggest")
def suggest(query: str = "") -> list:
    """Autocomplete Start/Destination from the local POI-name index."""
    from discoverroute.routing.geocode import suggest as _suggest
    typed = (query or "").strip()
    matches = list(_suggest(typed))
    if typed and typed not in matches:
        matches = [typed] + matches
    return matches or ([typed] if typed else [])


@app.api(name="plan")
def plan(start: str, dest: str, mode: str = "walk", budget: float = 0.5,
         vibe: str = "", adventurousness: float = 0.3,
         prefer_green: float = 0.0, prefer_quiet: float = 0.0,
         profile: str = "") -> dict:
    """Plan a route and return everything the custom frontend renders."""
    try:
        profile_obj = json.loads(profile) if profile else {}
    except Exception:  # noqa: BLE001
        profile_obj = {}

    result = plan_route(
        start_query=start, dest_query=dest, mode=mode, budget=budget, vibe=vibe,
        adventurousness=adventurousness, prefer_green=prefer_green,
        prefer_quiet=prefer_quiet, profile=profile_obj, n_alternatives=N_ALTERNATIVES,
    )

    if result.error:
        return {
            "error": result.error,
            "map_html": mapui.empty_map("Hmm — " + result.error.split(". ")[0].rstrip(".") + "."),
        }

    geo = {
        "start": list(result.start) if result.start else None,
        "end": list(result.end) if result.end else None,
        "mode": (mode or "walk").lower(),
        "start_label": start, "end_label": dest,
    }

    alts = result.alternatives or []
    if not alts:  # honest no-detour (or budget 0): plain route + stump state
        return {
            "error": None,
            "no_detour": True,
            "map_html": mapui.render_routes(
                plain=result.plain, start=result.start, end=result.end),
            "summary_md": result.summary_md,
            "interpretation_md": result.interpretation_md,
            "itinerary_md": result.itinerary_md,
            "nodetour_html": _nodetour_html(),
            "alternatives": [],
            "last_cats": [],
            "export": _export_data(result.plain, []),
            **geo,
        }

    alternatives = []
    for i, alt in enumerate(alts):
        alternatives.append({
            "label": _alt_label(i, alt, result.plain),
            "map_html": mapui.render_routes(
                plain=result.plain, discovery=alt.discovery, pois=alt.pois,
                start=result.start, end=result.end),
            "summary_md": alt.summary_md,
            "itinerary_md": alt.itinerary_md,
            "export": _export_data(alt.discovery, alt.pois),
        })

    return {
        "error": None,
        "no_detour": False,
        "interpretation_md": result.interpretation_md,
        "alternatives": alternatives,
        "last_cats": [p.category for p in alts[0].pois],
        **geo,
    }


def _export_data(route, pois) -> dict:
    """Lat/lon waypoints + the real polyline, so the browser can build a Google/
    Apple Maps link or a GPX file without re-planning."""
    from discoverroute.data import taxonomy
    return {
        "waypoints": [
            {"lat": round(p.lat, 6), "lon": round(p.lon, 6),
             "name": taxonomy.display_label(p)}
            for p in (pois or [])
        ],
        "coords": [[round(c[0], 6), round(c[1], 6)]
                   for c in (getattr(route, "coords", None) or [])],
    }


def _nodetour_html() -> str:
    from discoverroute.ui import design
    return design.NO_DETOUR_HTML


@app.get("/", response_class=HTMLResponse)
def homepage() -> str:
    return shell.index_html()


def warmup() -> None:
    """Preload graph + CSR + POIs + the vibe embedder so the first request is fast."""
    try:
        from discoverroute.routing import graph as g
        from discoverroute.routing import pois as poimod
        g.load_graph()
        g.graph_csr()
        poimod.load_pois()
        print("[warmup] routing graph + POIs ready", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"[warmup] graph FAILED: {exc}", flush=True)
    try:
        from discoverroute.interpret import embed
        embed.vibe_to_affinity("quiet green wander")
        print("[warmup] vibe embedder ready", flush=True)
    except Exception as exc:  # noqa: BLE001
        print(f"[warmup] embedder skipped: {exc}", flush=True)


if __name__ == "__main__":
    warmup()
    # _frontend=False: do NOT mount Gradio's default SPA at "/", so our custom
    # app-shell route (@app.get("/")) wins. The @app.api endpoints + @gradio/client
    # queue still work (that's the API engine, independent of the default UI).
    app.launch(show_error=True, _frontend=False)
