# Deploying DiscoverRoute to a Hugging Face Space

The project is push-ready: `app.py` + `README.md` (Space card) at the root,
`requirements.txt` pinned, and the offline artifacts (`data/paris_walk.graphml`
~90 MB, `data/paris_pois.parquet`) committed via Git LFS so the Space needs **no
runtime OSM download**.

## One-time

```bash
# from the project root
cd discoverroute

# 1. Auth + LFS
pip install -U "huggingface_hub[cli]"
hf auth login                       # paste a WRITE token from hf.co/settings/tokens
git lfs install

# 2. Create the Space (Gradio SDK). Use your username in the REPO_ID.
hf repos create <your-username>/discoverroute --type space --space-sdk gradio
#   -> creates https://huggingface.co/spaces/<your-username>/discoverroute
```

## Push

This folder is nested inside another git repo, so give it its own repo for the Space:

```bash
cd discoverroute
git init                            # fresh repo just for the Space
git lfs track "*.graphml" "*.parquet"   # already declared in .gitattributes
git add -A
git commit -m "DiscoverRoute v1 — taste-aware Paris detour routing"
git remote add origin https://huggingface.co/spaces/<your-username>/discoverroute
git push -u origin main             # LFS uploads the graph (~90 MB) automatically
```

`.gitignore` already excludes `.venv/`, `cache/`, and Gradio scratch — only the
app, source, tests, and `data/` artifacts are pushed.

## Enable the narration LLM (optional)

The app runs CPU-only out of the box (grounded **template** narration + keyword/
embedding vibe weights). To turn on the in-Space MiniCPM5-1B generative path:

1. In the Space **Settings → Hardware**, select a **ZeroGPU** tier.
2. The `@spaces.GPU` decorator on `narrate/llm.py::run_inference` activates
   automatically. Vibe→weights (Call 1) and narration (Call 2) only call the model
   when a GPU is present, and **fall back to the keyword matcher / grounded template
   if the model is absent or its output fails validation / the zero-hallucination
   gate** — so the app is correct either way. Weights are pulled from the HF Hub.

To force the LLM on/off regardless of hardware, set the Space variable
`DISCOVERROUTE_USE_LLM` to `1` / `0`.

## Off the Grid — no external APIs

DiscoverRoute is OSM-only: there is **no** Google Places (or any cloud) dependency.
Open-now comes from OSM `opening_hours` tags (~31% of POIs carry them); the 1B model
runs inside the Space on ZeroGPU. Nothing leaves the Space at request time.

## Open Trace — optional inference trace dataset

Every model call logs a row to `logs/traces.jsonl`. To also publish them to an HF
Dataset, set the Space **secret** `HF_TOKEN` (write scope) — rows are then pushed
async to `DISCOVERROUTE_TRACE_REPO` (default `build-small-hackathon/discoverroute-traces`).
Without the token, logging stays local (graceful no-op).

## Refreshing the data snapshot

Place data is a build-time snapshot. To refresh it (e.g. before a demo):
```bash
rm -rf cache/   # drop the Overpass HTTP cache to force a fresh download
.venv/bin/python -m discoverroute.data.build_graph   # ~3 min
.venv/bin/python -m discoverroute.data.build_pois    # ~12 min
```
OSM edits typically reach Overpass within minutes, so a rebuild is near-live.

## Notes
- First boot loads the 90 MB graph (~9 s, one-time); warm requests are ~1 s.
- If you ever rebuild the data: `python -m discoverroute.data.build_graph` then
  `python -m discoverroute.data.build_pois`, and re-commit `data/`.
- Free Space storage comfortably fits the ~91 MB of LFS artifacts.
