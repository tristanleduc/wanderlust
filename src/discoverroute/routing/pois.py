"""Runtime POI access: load the cached POI table and select corridor candidates.

The corridor is a buffer around the direct route whose half-width grows with the
detour budget. Distances are computed in a local equirectangular projection
(metres) around Paris centre — accurate to well under a metre at city scale and
far cheaper than per-request geopandas reprojection.
"""
from __future__ import annotations

import functools
import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
import shapely

from discoverroute import config

# Local equirectangular projection constants (metres per degree near Paris).
_LAT0, _LON0 = config.PARIS_CENTER
_M_PER_DEG_LAT = 110_540.0
_M_PER_DEG_LON = 111_320.0 * math.cos(math.radians(_LAT0))


@dataclass
class POI:
    osm_type: str
    osm_id: int
    name: str | None
    lat: float
    lon: float
    category: str
    greenness: float
    quietness: float
    confidence: float
    n_tags: int
    opening_hours: str | None = None
    # filled by the scorer (Brick 2):
    score: float = 0.0
    # filled by hours.apply_open_now: True / False / None (unknown)
    open_state: bool | None = None


def _to_metres(lat, lon):
    x = (np.asarray(lon) - _LON0) * _M_PER_DEG_LON
    y = (np.asarray(lat) - _LAT0) * _M_PER_DEG_LAT
    return x, y


@functools.lru_cache(maxsize=1)
def _load_table():
    """Load the POI parquet once and precompute metric coordinates + points."""
    if not config.POIS_PATH.exists():
        raise FileNotFoundError(
            f"POI table not found at {config.POIS_PATH}. "
            "Run: python -m discoverroute.data.build_pois"
        )
    df = pd.read_parquet(config.POIS_PATH)
    xs, ys = _to_metres(df["lat"].to_numpy(), df["lon"].to_numpy())
    df = df.assign(_x=xs, _y=ys)
    points = shapely.points(xs, ys)
    tree = shapely.STRtree(points)  # spatial index for fast corridor queries
    return df, points, tree


def load_pois() -> pd.DataFrame:
    return _load_table()[0]


def _route_line_metres(coords: list[tuple[float, float]]):
    """Shapely LineString of a (lat, lon) route in local metres."""
    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]
    xs, ys = _to_metres(lats, lons)
    return shapely.linestrings(np.column_stack([xs, ys]))


def corridor_pois(
    route_coords: list[tuple[float, float]],
    budget: float,
    max_candidates: int = config.MAX_CANDIDATES,
) -> list[POI]:
    """POIs within the budget-scaled corridor around a route polyline.

    Uses an STRtree spatial index (avoids scanning all ~30k POIs). When the
    corridor holds more than ``max_candidates``, keeps the ones *closest to the
    route* (geographically most relevant) rather than the best-tagged ones —
    so dense, well-mapped commercial strips don't crowd out nearby low-tag gems.
    """
    df, points, tree = _load_table()
    if not route_coords or len(route_coords) < 2:
        return []
    line = _route_line_metres(route_coords)
    halfwidth = config.corridor_halfwidth_m(budget)

    idx = tree.query(line, predicate="dwithin", distance=halfwidth)
    if len(idx) == 0:
        return []
    sel = df.iloc[idx].copy()
    sel["_corridor_dist"] = shapely.distance(points.take(idx), line)
    if len(sel) > max_candidates:
        sel = sel.nsmallest(max_candidates, "_corridor_dist")

    return [
        POI(
            osm_type=r.osm_type,
            osm_id=int(r.osm_id),
            name=None if pd.isna(r.name) else r.name,
            lat=float(r.lat),
            lon=float(r.lon),
            category=r.category,
            greenness=float(r.greenness),
            quietness=float(r.quietness),
            confidence=float(r.confidence),
            n_tags=int(r.n_tags),
            opening_hours=(None if pd.isna(getattr(r, "opening_hours", None))
                           else str(r.opening_hours)),
        )
        for r in sel.itertuples(index=False)
    ]
