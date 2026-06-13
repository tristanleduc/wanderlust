"""Resolve a routable *area* for a request — Paris (pre-baked) or any city live.

Paris ships as a cached graph + POI table: instant and offline. Anywhere else is
fetched from OpenStreetMap at request time, but only the bounding box spanning
the two endpoints (plus a margin) — not the whole metropolis. That keeps a
"route across Tokyo" download to a few MB that builds in seconds, and lets the
exact same corridor → score → orienteering pipeline run anywhere on Earth.

An ``Area`` bundles everything the pipeline needs that used to be Paris globals:
the routing graph, the POI table (indexed for corridor queries about a local
projection origin), a timezone for honest "open now" badges, and a label.
"""
from __future__ import annotations

import functools
import logging
import math
import os
import time
from dataclasses import dataclass
from zoneinfo import ZoneInfo

import osmnx as ox
import pandas as pd

from discoverroute import config
from discoverroute.routing import pois as poimod

logger = logging.getLogger("discoverroute")

_M_PER_DEG_LAT = 110_540.0


@dataclass
class Area:
    """A routable region: graph + POIs + projection origin + timezone."""
    key: str
    label: str
    graph: object                 # networkx MultiDiGraph
    table: tuple                  # (df, points, STRtree) from poimod.index_table
    csr: tuple                    # (csr, nodes, idx) for the travel matrix
    origin: tuple[float, float]   # (lat0, lon0) for the local metric projection
    tz: ZoneInfo
    source: str                   # "paris-cached" | "on-demand"
    attribution: str = "© OpenStreetMap contributors (ODbL)"


def _haversine_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    (lat1, lon1), (lat2, lon2) = a, b
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _coarse_tz(lat: float, lon: float) -> ZoneInfo:
    """Best-effort timezone for honest 'open now' badges.

    Uses ``timezonefinder`` when installed (precise); otherwise falls back to a
    coarse longitude→UTC-offset guess. The badge logic abstains on ambiguity, so
    a rough offset only ever shifts the day-boundary, never invents an opening.
    """
    try:
        from timezonefinder import TimezoneFinder
        name = TimezoneFinder().timezone_at(lat=lat, lng=lon)
        if name:
            return ZoneInfo(name)
    except Exception:  # noqa: BLE001 - dep missing or no match => coarse fallback
        pass
    offset = max(-12, min(14, round(lon / 15.0)))
    try:
        return ZoneInfo(f"Etc/GMT{-offset:+d}")  # Etc/GMT signs are inverted
    except Exception:  # noqa: BLE001
        return ZoneInfo("UTC")


def _bbox_around(start, end):
    """(left, bottom, right, top) = (W, S, E, N) bbox around A→B + margin."""
    lats = [start[0], end[0]]
    lons = [start[1], end[1]]
    lat0 = sum(lats) / 2
    # Convert the metre margin to degrees at this latitude.
    dlat = config.ON_DEMAND_MARGIN_M / _M_PER_DEG_LAT
    dlon = config.ON_DEMAND_MARGIN_M / (111_320.0 * max(0.1, math.cos(math.radians(lat0))))
    return (min(lons) - dlon, min(lats) - dlat,
            max(lons) + dlon, max(lats) + dlat)


def _features_to_table(gdf) -> pd.DataFrame:
    """Classify on-demand OSM features into the same schema as the Paris parquet."""
    from discoverroute.data import taxonomy
    from discoverroute.data.build_pois import _point_of, _row_tags

    records = []
    for idx, row in gdf.iterrows():
        tags = _row_tags(row)
        category = taxonomy.classify(tags)
        if category is None:
            continue
        pt = _point_of(row.geometry)
        if pt is None:
            continue
        osm_type, osm_id = (idx if isinstance(idx, tuple) else ("node", idx))
        name = tags.get("name")
        hours = tags.get("opening_hours")
        records.append({
            "osm_type": str(osm_type),
            "osm_id": int(osm_id),
            "name": str(name) if name is not None else None,
            "lat": float(pt[0]),
            "lon": float(pt[1]),
            "category": category,
            "greenness": taxonomy.greenness(category),
            "quietness": taxonomy.quietness(category),
            "confidence": round(taxonomy.confidence(tags), 4),
            "n_tags": len(tags),
            "opening_hours": str(hours) if hours is not None else None,
        })
    return pd.DataFrame.from_records(records)


def _fetch_pois(bbox) -> pd.DataFrame:
    """Download POIs over a bbox, one tag key at a time (lighter on Overpass)."""
    from discoverroute.data import taxonomy

    frames = []
    for key in taxonomy.OSM_QUERY_TAGS:
        try:
            part = ox.features_from_bbox(bbox, {key: True})
        except Exception as exc:  # noqa: BLE001 - a dry tag key is normal
            logger.debug("on-demand POI key %r failed: %s", key, exc)
            continue
        if len(part):
            frames.append(part)
    if not frames:
        return pd.DataFrame()
    gdf = pd.concat(frames)
    gdf = gdf[~gdf.index.duplicated(keep="first")]
    return _features_to_table(gdf)


@functools.lru_cache(maxsize=1)
def _paris_area() -> Area:
    """The pre-baked Paris area (cached graph + parquet), wrapped as an Area."""
    from discoverroute.routing import graph as g

    return Area(
        key="paris",
        label="Paris",
        graph=g.load_graph(),
        table=poimod._load_table(),
        csr=g.graph_csr(),
        origin=config.PARIS_CENTER,
        tz=ZoneInfo("Europe/Paris"),
        source="paris-cached",
    )


def city_bbox(slug: str):
    """(left, bottom, right, top) box for a pre-baked city — matches build_city."""
    spec = config.CITIES[slug]
    lat, lon = spec["center"]
    r = spec["radius_m"]
    dlat = r / 110_540.0
    dlon = r / (111_320.0 * max(0.1, math.cos(math.radians(lat))))
    return (lon - dlon, lat - dlat, lon + dlon, lat + dlat)


def _in_bbox(pt, bbox) -> bool:
    return bbox[0] <= pt[1] <= bbox[2] and bbox[1] <= pt[0] <= bbox[3]


def available_cities() -> list[str]:
    """Slugs of pre-baked cities whose data is actually present on disk."""
    return [s for s in config.CITIES
            if config.city_graph_path(s).exists() and config.city_pois_path(s).exists()]


@functools.lru_cache(maxsize=8)
def _city_area(slug: str) -> Area:
    """Load a pre-baked city (committed graph + parquet) as an offline Area."""
    from discoverroute.routing import graph as g

    spec = config.CITIES[slug]
    graph = ox.load_graphml(config.city_graph_path(slug))
    df = pd.read_parquet(config.city_pois_path(slug))
    origin = tuple(spec["center"])
    return Area(
        key=slug, label=spec["label"], graph=graph,
        table=poimod.index_table(df, origin), csr=g.build_csr(graph),
        origin=origin, tz=ZoneInfo(spec["tz"]), source="prebaked",
    )


# Manual bounded LRU of on-demand areas (graphs are heavy — keep only a few).
_ondemand_cache: dict[str, Area] = {}
_ondemand_order: list[str] = []


def _bbox_key(bbox) -> str:
    # Round to ~100 m so near-identical requests reuse one fetched area.
    return ",".join(f"{v:.3f}" for v in bbox)


def _build_ondemand(bbox, label: str) -> Area:
    key = _bbox_key(bbox)
    if key in _ondemand_cache:
        return _ondemand_cache[key]

    ox.settings.requests_timeout = config.ON_DEMAND_FETCH_TIMEOUT
    ox.settings.use_cache = True
    t0 = time.time()
    logger.info("on-demand: building area %s for bbox %s", label, key)
    from discoverroute.routing.graph import RouteError

    try:
        graph = ox.graph_from_bbox(bbox, network_type="walk")
        graph = ox.truncate.largest_component(graph, strongly=True)
    except Exception as exc:  # noqa: BLE001
        raise RouteError(
            f"Couldn't load the street network for {label} from OpenStreetMap "
            "(the map service may be busy). Please try again in a moment."
        ) from exc

    from discoverroute.routing.graph import build_csr

    df = _fetch_pois(bbox)
    origin = ((bbox[1] + bbox[3]) / 2, (bbox[0] + bbox[2]) / 2)  # (lat, lon) centre
    table = poimod.index_table(df, origin) if len(df) else (df, None, None)
    tz = _coarse_tz(*origin)
    logger.info("on-demand: %s ready — %d nodes, %d POIs in %.1fs",
                label, graph.number_of_nodes(), len(df), time.time() - t0)

    area = Area(key=key, label=label, graph=graph, table=table,
                csr=build_csr(graph), origin=origin, tz=tz, source="on-demand")
    _ondemand_cache[key] = area
    _ondemand_order.append(key)
    while len(_ondemand_order) > config.AREA_CACHE_SIZE:
        evict = _ondemand_order.pop(0)
        _ondemand_cache.pop(evict, None)
    return area


def resolve_area(start: tuple[float, float], end: tuple[float, float],
                 label: str = "") -> Area:
    """Pick the right area for an A→B request.

    Both endpoints inside Paris => the instant pre-baked area. Otherwise fetch a
    just-big-enough box around the two points live from OSM. Endpoints too far
    apart for an on-demand box are rejected with a friendly RouteError.
    """
    from discoverroute.routing.graph import RouteError

    # 1) Paris — full pre-baked city (instant, offline).
    if config.in_paris(*start) and config.in_paris(*end):
        return _paris_area()

    # 2) Other pre-baked cities (instant, offline) — both points in one city core.
    for slug in available_cities():
        bbox = city_bbox(slug)
        if _in_bbox(start, bbox) and _in_bbox(end, bbox):
            return _city_area(slug)

    # 3) Anywhere else. Offline mode (the "Off the Grid" deploy config) only knows
    # the pre-baked cities, so say so honestly. Online mode fetches live from OSM.
    if os.environ.get(config.OFFLINE_ENV_VAR) == "1":
        covered = ", ".join(["Paris"] + [config.CITIES[s]["label"] for s in available_cities()])
        raise RouteError(
            f"WanderLust covers {covered}. Pick a start and destination within one "
            "of these cities (this build runs fully offline)."
        )

    dist = _haversine_m(start, end)
    if dist > config.MAX_ENDPOINT_DISTANCE_M:
        raise RouteError(
            f"Those points are {dist / 1000:.0f} km apart — too far for a single "
            "walkable/bikeable discovery route. Pick start and end within the "
            f"same city (under {config.MAX_ENDPOINT_DISTANCE_M / 1000:.0f} km)."
        )
    return _build_ondemand(_bbox_around(start, end), label or "this area")
