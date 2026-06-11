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

The app runs CPU-only out of the box (grounded **template** narration). To turn on
the Qwen3.5-9B generative narration:

1. In the Space **Settings → Hardware**, select a **ZeroGPU** tier.
2. The `@spaces.GPU` decorator on `narrate/llm.py::generate` activates automatically.
   `narrate()` only calls the LLM when a GPU is present, and **falls back to the
   grounded template if the LLM output fails the zero-hallucination gate** — so the
   0% gate holds either way.

To force the LLM on/off regardless of hardware, set the Space variable
`DISCOVERROUTE_USE_LLM` to `1` / `0`.

## Notes
- First boot loads the 90 MB graph (~9 s, one-time); warm requests are ~1 s.
- If you ever rebuild the data: `python -m discoverroute.data.build_graph` then
  `python -m discoverroute.data.build_pois`, and re-commit `data/`.
- Free Space storage comfortably fits the ~91 MB of LFS artifacts.
