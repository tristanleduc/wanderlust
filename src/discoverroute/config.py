"""Central configuration: paths, Paris bounds, travel constants, defaults.

Everything tunable lives here so behaviour is inspectable, not scattered.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

# --- Paths -------------------------------------------------------------------
PKG_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PKG_ROOT.parent.parent
CACHE_DIR = PROJECT_ROOT / "cache"
DATA_DIR = PROJECT_ROOT / "data"
CACHE_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# Cached offline artifacts (committed for the Space; built by data/build_graph.py).
GRAPH_WALK_PATH = DATA_DIR / "paris_walk.graphml"
POIS_PATH = DATA_DIR / "paris_pois.parquet"

# --- Data provenance / freshness --------------------------------------------
# The app runs on a static OSM snapshot; this manifest (written by build_pois.py)
# records when it was built so the UI can show an honest "as of <date>" line.
DATA_MANIFEST_PATH = DATA_DIR / "build_manifest.json"


def _load_manifest() -> dict:
    try:
        return json.loads(DATA_MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - missing/invalid manifest is non-fatal
        return {}


DATA_MANIFEST = _load_manifest()
DATA_BUILD_DATE = DATA_MANIFEST.get("build_date", "")  # ISO 'YYYY-MM-DD' or ''

# --- Geographic scope --------------------------------------------------------
# Paris proper (the 20 arrondissements). Used to bound the OSM download and to
# reject out-of-area requests.
PARIS_PLACE = "Paris, Île-de-France, France"
# Bounding box (south, west, north, east) — a coarse rejection gate for inputs.
# Slightly padded beyond the périphérique.
PARIS_BBOX = (48.8156, 2.2241, 48.9022, 2.4699)  # (lat_min, lon_min, lat_max, lon_max)
PARIS_CENTER = (48.8566, 2.3522)

# --- Offline mode --------------------------------------------------------------
# When this env var is "1", geocoding never falls back to Nominatim (network):
# only the local POI-name index and 'lat, lon' inputs are accepted.
OFFLINE_ENV_VAR = "DISCOVERROUTE_OFFLINE"

# --- Travel model ------------------------------------------------------------
# Used to convert edge length (metres) into travel time (seconds).
TRAVEL_SPEEDS_KMH = {
    "walk": 4.8,
    "bike": 15.0,
}
DEFAULT_MODE = "walk"

# --- Detour budget defaults --------------------------------------------------
# budget is a fraction of direct-route time the user is willing to add.
# 0.0 => route equals the plain route. 1.0 => allow up to 2x the direct time.
DEFAULT_BUDGET = 0.5
MAX_BUDGET = 2.0

# --- Corridor (candidate gathering) ------------------------------------------
# Half-width of the search corridor around the direct route, in metres. Grows
# with the detour budget: more budget => look further off the direct line.
# (Heuristic for spec open-question §12; tuned in Brick 2.)
CORRIDOR_BASE_M = 250.0
CORRIDOR_BUDGET_M = 500.0  # added per unit of budget
MAX_CANDIDATES = 600       # corridor cap (keep nearest-to-route; scoring is cheap)
SOLVER_CANDIDATES = 40     # shortlist (top-scoring) for the real travel matrix
MAX_DETOUR_STOPS = 12      # max POIs the orienteering route may include


def corridor_halfwidth_m(budget: float) -> float:
    return CORRIDOR_BASE_M + CORRIDOR_BUDGET_M * max(0.0, budget)


# --- Pre-baked extra cities (offline, keeps "Off the Grid") ------------------
# Paris ships full-city (above). These additional cities are baked as a bounded
# walkable core (centre + radius) by data/build_city.py and committed, so they
# route fully offline — no live OSM at request time. Add a city here, run
# `python -m discoverroute.data.build_city <slug>`, commit the data.
CITY_DATA_DIR = DATA_DIR / "cities"
CITIES_MANIFEST_PATH = CITY_DATA_DIR / "cities_manifest.json"
CITIES = {
    "london":    {"label": "London",    "center": (51.5118, -0.1230), "radius_m": 3200, "tz": "Europe/London"},
    "barcelona": {"label": "Barcelona", "center": (41.3870,  2.1700), "radius_m": 3200, "tz": "Europe/Madrid"},
    "newyork":   {"label": "New York",  "center": (40.7560, -73.9845), "radius_m": 3200, "tz": "America/New_York"},
}


def city_graph_path(slug: str) -> Path:
    return CITY_DATA_DIR / f"{slug}_walk.graphml"


def city_pois_path(slug: str) -> Path:
    return CITY_DATA_DIR / f"{slug}_pois.parquet"


# --- Other cities (on-demand) ------------------------------------------------
# Paris ships pre-baked (instant, offline). Any other city is fetched live from
# OpenStreetMap at request time: we download only the bounding box spanning the
# two endpoints (plus a margin), not the whole metropolis — turning a multi-GB
# city download into a few-MB box that builds in seconds.
ON_DEMAND_MARGIN_M = 900.0      # padding added around the A→B bbox (corridor room)
# Reject on-demand requests whose endpoints are absurdly far apart: a giant bbox
# would overrun the public OSM servers and the worker's memory. Paris (cached)
# is exempt from this cap.
MAX_ENDPOINT_DISTANCE_M = 25_000.0
AREA_CACHE_SIZE = 4             # how many on-demand city areas to keep in memory
# Time budget for a single on-demand OSM fetch (graph or one feature key).
ON_DEMAND_FETCH_TIMEOUT = 60


# --- Models (Brick 4 / 6) ----------------------------------------------------
# Small text encoder for vibe -> category affinity (CPU-friendly, offline).
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
# bge-v1.5 retrieval instruction, prepended to the query (the vibe) only.
EMBED_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "
# Generative model for vibe→weights extraction + narration. A 1B in-Space model
# (Tiny Titan ≤4B; weights pulled from the Hub and run on ZeroGPU). Standard
# LlamaForCausalLM architecture — no custom kernels.
LLM_MODEL = "openbmb/MiniCPM5-1B"

# --- Trace logging (Open Trace) ----------------------------------------------
# Every inference call logs a row locally to logs/traces.jsonl; when a write
# token is present, rows are ALSO pushed (async, non-blocking) to TRACE_REPO.
# No token => local-only (graceful stub; nothing blocks).
HF_TOKEN = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
TRACE_REPO = os.environ.get(
    "DISCOVERROUTE_TRACE_REPO", "build-small-hackathon/discoverroute-traces"
)

# Affinity floor: the least-matching category still keeps this much interest so
# the route can explore a little; the best-matching category maps to 1.0.
AFFINITY_FLOOR = 0.15
# Only the top-N matched categories drive a vibe route; the rest are zeroed so
# the long tail (ranks N+1..17) can't silently backfill stops with off-vibe
# filler (the adversarial review found the same statues/churches bleeding into
# 10+ unrelated routes via the floor). Sparse routes then end honestly short.
TOP_AFFINITY_CATEGORIES = 6
# A vibe whose BEST raw cosine to any category gloss is below this is a weak/
# out-of-vocabulary match (measured: real vibes peak 0.66-0.85; "brutalist
# architecture" 0.51, nonsense ~0.49). We still route, but the narration says so
# honestly instead of claiming "a match for your vibe".
WEAK_MATCH_SIMILARITY = 0.55
# For "hidden gems"-style vibes, exclude well-documented (famous) POIs: a place
# this richly tagged isn't off the beaten path. Confidence is the tag-richness
# proxy; Notre Dame etc. sit at ~1.0. (Only applied when a discovery cue fires.)
FAMOUS_CONFIDENCE = 0.85
# Below this cosine-similarity span across categories, a vibe is treated as
# off-domain/neutral rather than amplified into false preferences. Measured
# (bge-small, 16-vibe battery): gibberish "asdfqwer" spans 0.081; the LOWEST
# real vibe ("romantic evening stroll") spans 0.143; "take me somewhere
# beautiful" 0.152, "brutalist architecture" 0.148. So 0.18 (the prior value)
# wrongly neutralised genuine evocative vibes — collapsing them to an identical
# generic grab-bag. 0.10 sits just above gibberish, rescuing real vibes while
# still catching nonsense. (Abstract vibes have NO clean separation from
# nonsense by span alone — "quantum physics lecture" also spans 0.143 — but a
# weakly-themed route for them beats a deceptive default route.)
MIN_AFFINITY_SPAN = 0.10


# --- Adventurousness ---------------------------------------------------------
# 0.0 => only high-confidence, well-documented POIs.
# 1.0 => admit low-confidence / under-documented POIs (serendipity).
DEFAULT_ADVENTUROUSNESS = 0.3


def speed_ms(mode: str) -> float:
    """Travel speed in metres/second for the given mode."""
    kmh = TRAVEL_SPEEDS_KMH.get(mode, TRAVEL_SPEEDS_KMH[DEFAULT_MODE])
    return kmh * 1000.0 / 3600.0


def in_paris(lat: float, lon: float) -> bool:
    """True if a point falls inside the padded Paris bounding box."""
    lat_min, lon_min, lat_max, lon_max = PARIS_BBOX
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max
