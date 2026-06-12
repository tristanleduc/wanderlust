---
title: DiscoverRoute
emoji: 🗺️
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: 6.18.0
app_file: app.py
pinned: false
license: mit
---

# DiscoverRoute

You give a start, a destination, a free-text vibe, and an "adventurousness" level.
DiscoverRoute returns a walkable/bikeable route that **deliberately detours past
places matching your taste** — within a travel-time budget — plus a narrated
itinerary explaining why each place is on the path.

It runs on a small (≤32B) model and open OpenStreetMap data. Single city: **Paris**.

The core inversion: ordinary navigation minimizes time. DiscoverRoute treats extra
time as a *budget to spend on discovery*.

## Status

**Complete first version** — all P0 must-haves + persistent taste profile,
serendipity, alternative routes, offline geocoding, and a fully custom UI (the
"clay sticker" design). 42 tests passing, live-verified, deploy-ready. See `PROGRESS.md`
for the per-brick build log, `FIELD_NOTES.md` for the build story, and
`DEPLOY.md` to push.

## Features

- **Plain vs discovery route** on one map, with the time the detour buys you.
- **Vibe → route**: free-text mood (e.g. "quiet green wander") is matched to OSM
  categories by sentence embeddings (`bge-small-en-v1.5`) and reshapes the route.
- **Detour budget**: a single slider trading extra time for discovery; the route
  never exceeds `(1 + budget) ×` the direct time. Budget 0 = the plain route.
- **Diversity by design**: a submodular orienteering solver favours a park + a
  viewpoint + a bookshop over five cafés, within budget.
- **Adventurousness**: low → well-documented places; high → injects hidden gems.
- **Grounded narration**: an itinerary that names only real waypoints, behind a
  hard zero-hallucination gate (optional in-Space MiniCPM5-1B enhancer — a ≤4B
  Tiny Titan on ZeroGPU — gated by the same).
- **Alternative routes**: up to three genuinely distinct options.
- **Persistent taste profile**: standing preferences + saved places, per device,
  blended with each trip's mood. No accounts.

## Local development

```bash
uv venv --python 3.11
uv pip install -e .            # skeleton (Bricks 0-3)
uv pip install -e ".[ml,dev]"  # + vibe interpretation / narration + tests

# one-time offline data prep for Paris (downloads OSM, builds graph + POIs)
.venv/bin/python -m discoverroute.data.build_graph

# run the app
.venv/bin/python app.py
```

## Architecture

Offline (built once for Paris, cached): download OSM extract → build walk/bike
routing graph → extract POIs with features + confidence.

Runtime (per request): interpret vibe → score corridor POIs → plan detour
(orienteering solver) → trace real polyline → narrate + map overlay.

The model is load-bearing only in interpretation and narration. Routing is pure
classical algorithms (OSMnx + networkx + SciPy multi-source Dijkstra; the
orienteering solver is a custom greedy submodular heuristic).

Geocoding is local-first: named Paris places resolve against the cached POI
table with no network call (set `DISCOVERROUTE_OFFLINE=1` to forbid the
Nominatim fallback entirely). Map data © OpenStreetMap contributors (ODbL).
