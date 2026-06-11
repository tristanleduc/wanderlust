"""Central configuration: paths, Paris bounds, travel constants, defaults.

Everything tunable lives here so behaviour is inspectable, not scattered.
"""
from __future__ import annotations

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


# --- Models (Brick 4 / 6) ----------------------------------------------------
# Small text encoder for vibe -> category affinity (CPU-friendly, offline).
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
# bge-v1.5 retrieval instruction, prepended to the query (the vibe) only.
EMBED_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "
# Generative model for posture interpretation + narration (optional; ≤32B, ZeroGPU).
LLM_MODEL = "Qwen/Qwen3.5-9B"
# Affinity floor: the least-matching category still keeps this much interest so
# the route can explore a little; the best-matching category maps to 1.0.
AFFINITY_FLOOR = 0.15
# Below this cosine-similarity span across categories, a vibe is treated as
# off-domain/neutral rather than amplified into false preferences.
MIN_AFFINITY_SPAN = 0.04


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
