---
title: WanderLust
emoji: 🗺️
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: 6.18.0
python_version: '3.12'
app_file: app.py
pinned: true
license: apache-2.0
short_description: A-to-B routes through places you'll love
tags:
  - thousand-token-wood-track
  - badge-off-the-grid
  - badge-off-brand
  - badge-tiny-titan
  - badge-field-notes
  - openbmb
---

# WanderLust

### Spend your extra time on discovery.

Most navigation apps answer one question: *what's the fastest way there?* **WanderLust
asks a better one: what if those few extra minutes were a gift?** You tell it where you're
going and the kind of moment you're after — "a slow Sunday-morning kind of walk,"
"bookshops and quiet streets," "a lively café crawl" — and it threads you from A to B
**past the places you'll actually love**, then tells you, in your own words, why each
one is on your path. Same destination. A walk you'll remember instead of one you'll forget.

> One-liner: **WanderLust turns any walk from A to B into a personal discovery — routing
> you through places that match your taste, not just the fastest path.** Cities: **Paris,
> London, Barcelona, New York** — all routed **fully offline** (no cloud APIs at request time).

---

## 🔗 Links (judges start here)

- **🎬 Demo video:** _TBA_
- **📣 Social post:** _TBA_
- **🧑‍🤝‍🧑 Team:** [Ishrat Jahan Ananya](TBA) · [Tristan Leduc](TBA)

---

## Why the AI is load-bearing

WanderLust **cannot work without the model.** The hard problem isn't routing — it's the
gap between how people describe what they want and what a router can optimize. A user
types a fuzzy, open-ended vibe ("somewhere that feels like a slow Sunday morning"), and
**MiniCPM5-1B converts it into concrete, scored routing weights** across 17 place
categories plus quiet/green/lively modifiers. No lookup table, keyword list, or rule
engine can map unbounded human mood onto a route — the model *is* the bridge. It then
writes the itinerary that explains why each chosen stop matches what you asked for,
grounded so it can only name real places on your route.

(When no GPU is allocated, the app degrades gracefully to an embedding + keyword
interpreter and a deterministic template — it never breaks — but the model is what makes
the experience feel like it read your mind.)

## The tech, one sentence each

- **Model — `openbmb/MiniCPM5-1B`:** a 1B-parameter model does two jobs — vibe → routing
  weights (JSON), and route → first-person itinerary narration.
- **ZeroGPU:** the model runs **inside the Space** on HF ZeroGPU via `@spaces.GPU`,
  weights pulled from the Hub — no external inference API, nothing leaves the Space.
- **OpenStreetMap + OSMnx:** walking/biking graphs and POIs for **Paris, London,
  Barcelona and New York**, pre-built and cached offline (Git LFS) so every city is
  instant — and routes with **no cloud API calls at request time** (Off the Grid).
- **Routing — classical, exact:** a `networkx` + SciPy multi-source Dijkstra travel-time
  matrix, solved by a custom **orienteering** (prize-collecting TSP) heuristic with
  submodular diversity — so you get a park + a viewpoint + a bookshop, not five cafés.
- **Frontend — Gradio `gr.Server`:** a hand-built HTML/CSS/JS app-shell on Gradio's
  FastAPI backend, called from the browser via `@gradio/client` — **no default Gradio UI**.

## What it does

- **Plain vs. discovery route** drawn on one map, with the exact time the detour buys you.
- **Vibe → route:** free-text mood reshapes which places the route seeks out.
- **Detour budget:** one slider trades extra time for discovery; the route never exceeds
  `(1 + budget) ×` the direct time. Budget 0 = the plain fastest route.
- **Adventurousness:** low → well-documented places; high → injects hidden gems.
- **Grounded narration:** an itinerary naming only real waypoints, behind a hard
  zero-hallucination gate.
- **Alternative routes:** up to three genuinely distinct options.
- **Persistent taste profile:** standing preferences + saved places, per device, blended
  with each trip's mood. No accounts.

## Badges we're claiming (and why)

| Badge | Justification |
|---|---|
| **Off-Brand** | Custom `gr.Server` app-shell — hand-built frontend, **zero default Gradio components**. |
| **Tiny Titan** | **MiniCPM5-1B — 1B parameters** (well under the 4B cap), running in-Space on ZeroGPU. |
| **Best Agent** | A four-stage pipeline: **vibe→weights extraction → POI scoring → orienteering solve → grounded narration.** |
| **Best Demo** | End-to-end Paris route from a single free-text vibe — see the demo video above. |
| **openbmb** | Built on OpenBMB's MiniCPM5-1B as the core reasoning model. |

> We also run **OSM-only with the model in-Space** (no external/cloud APIs at request
> time) and **log every inference call** to `logs/traces.jsonl` (optionally pushed to an
> HF Dataset) — supporting the *Off the Grid* and *Open Trace* narratives.

## Run it locally

```bash
uv venv --python 3.11
uv pip install -e ".[ml,dev]"   # routing + vibe interpretation/narration + tests

# one-time offline data prep for Paris (downloads OSM, builds the graph + POIs)
python -m discoverroute.data.build_graph
python -m discoverroute.data.build_pois

python app.py                   # serves the gr.Server app-shell on :7860
```

`65 tests passing` · See `DEPLOY.md` to push to a Space, `FIELD_NOTES.md` for the build
story, `PROGRESS.md` for the per-feature log.

## Architecture

**Offline (built once per city, cached):** OSM extract → walk/bike routing graph →
POIs with feature priors + confidence. Paris ships full-city; London, Barcelona and
New York are baked as walkable cores (`python -m discoverroute.data.build_city`).

**Runtime (per request):** pick the city → interpret vibe → score corridor POIs → solve
the detour (orienteering) → trace a real polyline → narrate + overlay on the map.

The model is load-bearing only in **interpretation and narration**; routing is pure
classical algorithms. Geocoding is local-first — named places resolve against the cached
POI index (Paris + every pre-baked city) with no network call. With
`DISCOVERROUTE_OFFLINE=1` (the deployed config) there are **zero cloud API calls at
request time** — routing is limited to the pre-baked cities. Map data © OpenStreetMap
contributors (ODbL).
