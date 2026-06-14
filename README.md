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
  - track:backyard
  - sponsor:openbmb
  - achievement:offgrid
  - achievement:offbrand
  - achievement:sharing
  - achievement:fieldnotes
  - badge-off-the-grid
  - badge-off-brand
  - badge-tiny-titan
  - badge-field-notes
  - openbmb
---

# WanderLust

### Spend your extra time on discovery.

**Track 1 — Backyard AI** · **Live Space:** https://huggingface.co/spaces/build-small-hackathon/WanderLust

Most navigation apps answer one question: *what's the fastest way there?* **WanderLust
asks a better one: what if those few extra minutes were a gift?** You tell it where you're
going and the kind of moment you're after — "a slow Sunday-morning kind of walk,"
"bookshops and quiet streets," "a lively café crawl" — and it threads you from A to B
**past the places you'll actually love**, then tells you, in your own words, why each
one is on your path. Same destination. A walk you'll remember instead of one you'll forget.

> One-liner: **WanderLust turns any walk or ride from A to B into a personal discovery —
> routing you through places that match your taste, not just the fastest path.** **Nine
> cities across four continents** — Paris, London, Barcelona, Berlin, New York, San
> Francisco, Tokyo, Mumbai, Shanghai — all routed **fully offline** (no cloud APIs at request time).

---

## Why we built it (Backyard AI)

This started as our own itch. We're cyclists, and pedaling around new cities we kept
hitting the same frustration: the map only ever knows the *fastest* line between two
points, but the whole joy of exploring your "backyard" — the city around you — is the
bookshop, the quiet square, the viewpoint you'd never have found on the direct route.
We wanted a tool that plans the *interesting* way from A to B, tuned to the mood we're in
that day. WanderLust is that tool: a personal, local-first exploration companion for the
ground right under your wheels.

## 🔗 Links (judges start here)

- **🗺️ Live Space:** https://huggingface.co/spaces/build-small-hackathon/WanderLust
- **💻 Source code (GitHub):** https://github.com/tristanleduc/wanderlust
- **🎬 Demo video:** https://www.youtube.com/watch?v=55Ofnt6Hhv4
- **📣 Social post:** [LinkedIn](https://www.linkedin.com/posts/ishrat-jahan-ananya_build-small-hackathon-build-small-hackathon-activity-7472015876708548609-Ss8T) · [X/Twitter](https://x.com/coreprinciple_/status/2066248778416267553)
- **📝 Field notes (HF blog):** https://huggingface.co/blog/coreprinciple/wanderlust
- **🧑‍🤝‍🧑 Team:**
  - **Ishrat Jahan Ananya** — [Hugging Face](https://huggingface.co/coreprinciple) · [GitHub](https://github.com/coreprinciple6) · [Website](https://coreprinciple.vercel.app/)
  - **Tristan Leduc** — [Hugging Face](https://huggingface.co/JohnDoe6) · [GitHub](https://github.com/tristanleduc) · [LinkedIn](https://www.linkedin.com/in/tristan-leduc-56491b188/)

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
- **OpenStreetMap + OSMnx:** walking/biking graphs and POIs for nine cities, pre-built and
  pulled from an open Hub dataset, then **pre-warmed at boot** so every city is instant —
  and routes with **no cloud API calls at request time** — fully offline.
- **Routing — classical, exact:** a `networkx` + SciPy multi-source Dijkstra travel-time
  matrix, solved by a custom **orienteering** (prize-collecting TSP) heuristic with
  submodular diversity — so you get a park + a viewpoint + a bookshop, not five cafés.
- **Frontend — Gradio `gr.Server`:** a hand-built HTML/CSS/JS app-shell on Gradio's
  FastAPI backend, called from the browser via `@gradio/client` — **no default Gradio UI**.

## What it does

- **Plain vs. discovery route** drawn on one map, with the exact time the detour buys you.
- **Vibe → route:** free-text mood reshapes which places the route seeks out.
- **Walk or bike**, across nine cities, with a city picker (cores pulled on demand).
- **Detour budget:** one slider trades extra time for discovery; the route never exceeds
  `(1 + budget) ×` the direct time. Budget 0 = the plain fastest route.
- **Adventurousness:** low → well-documented places; high → injects hidden gems.
- **Grounded narration:** an itinerary naming only real waypoints, behind a hard
  zero-hallucination gate.
- **Alternative routes:** up to three genuinely distinct options.
- **Persistent taste profile:** standing preferences + saved places, per device, blended
  with each trip's mood. No accounts.

## Achievements & badges we're claiming

**Achievements** (`achievement:*` tags):

| Achievement | How WanderLust earns it |
|---|---|
| **Off the Grid** (`offgrid`) | With `DISCOVERROUTE_OFFLINE=1`, **zero cloud APIs at request time** — every city is pre-baked + pre-warmed at boot, geocoding is local, and the 1B model runs in-Space on ZeroGPU. |
| **Off-Brand** (`offbrand`) | A hand-built `gr.Server` HTML/CSS/JS app-shell — **zero default Gradio components**: custom map, custom controls, custom live-map loader. |
| **Sharing is Caring** (`sharing`) | Two reusable artifacts shared publicly on the Hub: the city-cores dataset [`build-small-hackathon/discoverroute-cities`](https://huggingface.co/datasets/build-small-hackathon/discoverroute-cities) and the inference-trace dataset `build-small-hackathon/discoverroute-traces`. |
| **Field Notes** (`fieldnotes`) | The end-to-end build story — decisions, dead ends, fixes — in [`FIELD_NOTES.md`](FIELD_NOTES.md) and published as an **[HF blog post](https://huggingface.co/blog/coreprinciple/wanderlust)**. |

**Bonus badges** (prize categories) we're going for:

| Badge | Basis |
|---|---|
| **Off Brand** ($1,500) | The hand-built `gr.Server` custom UI (same evidence as the achievement). |
| **Tiny Titan** ($1,500) | **MiniCPM5-1B — 1B parameters** (well under the 4B cap), in-Space on ZeroGPU. |
| **Best Agent** ($1,000) | Four-stage planning pipeline: vibe → routing weights → POI scoring → orienteering solve → grounded narration. |


> **Sponsor prize:** built on OpenBMB's **MiniCPM5-1B**, so eligible for **Best MiniCPM Build** (OpenBMB).


## Run it locally

```bash
uv venv --python 3.11
uv pip install -e ".[ml,dev]"   # routing + vibe interpretation/narration + tests

# one-time offline data prep for Paris (downloads OSM, builds the graph + POIs)
python -m discoverroute.data.build_graph
python -m discoverroute.data.build_pois

python app.py                   # serves the gr.Server app-shell on :7860
```

The other eight cities are pulled on demand from the Hub dataset (and pre-warmed at boot).
Run the test suite with `pytest` (config in `pyproject.toml`, tests in `tests/`).
See [`FIELD_NOTES.md`](FIELD_NOTES.md) for the build story.

## Architecture

**Offline (built once per city, cached):** OSM extract → walk/bike routing graph →
POIs with feature priors + confidence. Paris ships full-city; the other eight (London,
Barcelona, Berlin, New York, San Francisco, Tokyo, Mumbai, Shanghai) are baked as walkable
cores via `python -m discoverroute.data.build_city` and hosted as an open Hub dataset, then
pulled + pre-warmed at boot.

**Runtime (per request):** pick the city → interpret vibe → score corridor POIs → solve
the detour (orienteering) → trace a real polyline → narrate + overlay on the map.

The model is load-bearing only in **interpretation and narration**; routing is pure
classical algorithms. Geocoding is local-first — named places resolve against the cached
POI index with no network call. With `DISCOVERROUTE_OFFLINE=1` (the deployed config) there
are **zero cloud API calls at request time** — routing is limited to the pre-baked cities.
Map data © OpenStreetMap contributors (ODbL).
