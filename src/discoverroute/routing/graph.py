"""Graph loading, geocoding, and plain (shortest) routing on the Paris network.

This is Brick 0: a connected walkable/bikeable path between two valid Paris
points, with distance and estimated time. Routing minimises distance (which, for
a fixed mode, minimises time) using networkx Dijkstra over the ``length`` edge
attribute.
"""
from __future__ import annotations

import functools
import logging
import os
from dataclasses import dataclass, field

import networkx as nx
import osmnx as ox

from discoverroute import config

logger = logging.getLogger("discoverroute")

# Runtime geocoding hits Nominatim. Keep the timeout short (a slow/blocked
# request must not pin a Space worker for the 180s default), and identify
# ourselves politely so we are not lumped in with the default OSMnx user-agent.
ox.settings.requests_timeout = 10
ox.settings.http_user_agent = "DiscoverRoute/0.1 (Paris detour planner; HF Space)"


class RouteError(ValueError):
    """Raised for invalid/out-of-bounds routing requests (not crashes)."""


@dataclass
class Route:
    """A traced path on the graph with derived distance and time."""

    nodes: list[int]
    coords: list[tuple[float, float]]  # (lat, lon) along the path, for the map
    distance_m: float
    mode: str
    waypoint_pois: list = field(default_factory=list)  # filled by later bricks
    dwell_s: float = 0.0  # planned lingering time at stops (P1-2)

    @property
    def time_s(self) -> float:
        return self.distance_m / config.speed_ms(self.mode)

    @property
    def time_min(self) -> float:
        return self.time_s / 60.0


@functools.lru_cache(maxsize=1)
def load_graph():
    """Load the cached Paris walk graph (singleton). Build it first if missing."""
    if not config.GRAPH_WALK_PATH.exists():
        raise RouteError(
            f"Routing graph not found at {config.GRAPH_WALK_PATH}. "
            "Run: python -m discoverroute.data.build_graph"
        )
    return ox.load_graphml(config.GRAPH_WALK_PATH)


@functools.lru_cache(maxsize=1)
def graph_csr():
    """Cached SciPy CSR adjacency (length-weighted) + node<->index maps.

    Enables C-speed multi-source Dijkstra for the travel matrix instead of dozens
    of pure-Python networkx runs. Parallel edges collapse to their minimum length.
    """
    from scipy.sparse import csr_matrix

    graph = load_graph()
    nodes = list(graph.nodes())
    idx = {n: i for i, n in enumerate(nodes)}
    best: dict[tuple[int, int], float] = {}
    for u, v, d in graph.edges(data=True):
        key = (idx[u], idx[v])
        length = d.get("length", 0.0)
        if key not in best or length < best[key]:
            best[key] = length
    rows = [k[0] for k in best]
    cols = [k[1] for k in best]
    data = list(best.values())
    csr = csr_matrix((data, (rows, cols)), shape=(len(nodes), len(nodes)))
    return csr, nodes, idx


@functools.lru_cache(maxsize=512)
def geocode_point(query: str) -> tuple[float, float]:
    """Resolve a free-text address or 'lat, lon' string to a (lat, lon) point.

    Cached: the demo defaults and repeated addresses don't re-hit Nominatim
    (which rate-limits at ~1 req/s). Failures raise and are not cached.
    Raises RouteError if it cannot be resolved or falls outside Paris.
    """
    query = (query or "").strip()
    if not query:
        raise RouteError("Empty location. Enter an address or 'lat, lon'.")

    # Try "lat, lon" first, then the offline POI-name index (no network needed).
    latlon = _try_parse_latlon(query)
    if latlon is None:
        from discoverroute.routing.geocode import is_world_place, local_geocode

        if is_world_place(query):
            raise RouteError(
                f"{query!r} looks like a place outside Paris — DiscoverRoute "
                "covers Paris only. Try a Paris landmark (e.g. 'Louvre')."
            )
        latlon = local_geocode(query)
    if latlon is None:
        if os.environ.get(config.OFFLINE_ENV_VAR) == "1":
            raise RouteError(
                f"Could not find {query!r} in the local Paris place index "
                f"(offline mode, {config.OFFLINE_ENV_VAR}=1). "
                "Try a named Paris place (e.g. 'Jardin du Luxembourg') "
                "or enter 'lat, lon'."
            )
        try:
            lat, lon = ox.geocode(query)
        except Exception as exc:  # noqa: BLE001 - surface a clean message
            logger.warning("geocode failed for %r: %s: %s",
                           query, type(exc).__name__, exc)
            raise RouteError(
                f"Could not find a location for {query!r}. "
                "Try a more specific Paris address or enter 'lat, lon'."
            ) from exc
    else:
        lat, lon = latlon

    if not config.in_paris(lat, lon):
        raise RouteError(
            f"Location {query!r} ({lat:.4f}, {lon:.4f}) is outside Paris. "
            "DiscoverRoute v1 covers Paris only."
        )
    return lat, lon


def _try_parse_latlon(query: str) -> tuple[float, float] | None:
    parts = query.replace(";", ",").split(",")
    if len(parts) != 2:
        return None
    try:
        lat, lon = float(parts[0].strip()), float(parts[1].strip())
    except ValueError:
        return None
    return lat, lon


def nearest_node(graph, lat: float, lon: float) -> int:
    """Nearest graph node to a (lat, lon) point. (osmnx wants lon=X, lat=Y.)"""
    return int(ox.distance.nearest_nodes(graph, X=lon, Y=lat))


def edge_length(graph, u: int, v: int) -> float:
    """Length in metres of the shortest parallel edge between u and v."""
    data = graph.get_edge_data(u, v)
    return min(d.get("length", 0.0) for d in data.values())


def path_length_m(graph, nodes: list[int]) -> float:
    return sum(edge_length(graph, u, v) for u, v in zip(nodes[:-1], nodes[1:]))


def path_coords(graph, nodes: list[int]) -> list[tuple[float, float]]:
    """(lat, lon) polyline for a node path, following edge geometry when present."""
    if not nodes:
        return []
    coords: list[tuple[float, float]] = []
    for u, v in zip(nodes[:-1], nodes[1:]):
        data = graph.get_edge_data(u, v)
        best = min(data.values(), key=lambda d: d.get("length", float("inf")))
        geom = best.get("geometry")
        if geom is not None:
            pts = [(y, x) for x, y in geom.coords]  # shapely is (x=lon, y=lat)
        else:
            pts = [
                (graph.nodes[u]["y"], graph.nodes[u]["x"]),
                (graph.nodes[v]["y"], graph.nodes[v]["x"]),
            ]
        if coords and coords[-1] == pts[0]:
            coords.extend(pts[1:])
        else:
            coords.extend(pts)
    return coords


def shortest_path_nodes(graph, orig: int, dest: int) -> list[int]:
    """Dijkstra node path minimising edge length. Raises RouteError if none."""
    try:
        return nx.shortest_path(graph, orig, dest, weight="length")
    except nx.NetworkXNoPath as exc:
        raise RouteError("No connected path between those points.") from exc


def stitch_route(graph, waypoint_nodes: list[int], mode=config.DEFAULT_MODE,
                 waypoint_pois=None) -> Route:
    """Stitch shortest paths between consecutive waypoints into one Route.

    ``waypoint_nodes`` = [start_node, poi_node, ..., end_node]. Consecutive
    duplicate waypoints are skipped. Used by Brick 3 to turn the solver's ordered
    POI sequence into a single real polyline.
    """
    full: list[int] = []
    for u, v in zip(waypoint_nodes[:-1], waypoint_nodes[1:]):
        if u == v:
            continue
        leg = shortest_path_nodes(graph, u, v)
        if full and full[-1] == leg[0]:
            full.extend(leg[1:])
        else:
            full.extend(leg)
    if not full:
        full = [waypoint_nodes[0]]
    return Route(
        nodes=full,
        coords=path_coords(graph, full),
        distance_m=path_length_m(graph, full),
        mode=mode,
        waypoint_pois=list(waypoint_pois or []),
    )


def plain_route(graph, orig_lat, orig_lon, dest_lat, dest_lon, mode=config.DEFAULT_MODE) -> Route:
    """The shortest-path (plain) route between two points — the speed baseline."""
    orig = nearest_node(graph, orig_lat, orig_lon)
    dest = nearest_node(graph, dest_lat, dest_lon)
    if orig == dest:
        raise RouteError("Start and destination resolve to the same point.")
    nodes = shortest_path_nodes(graph, orig, dest)
    return Route(
        nodes=nodes,
        coords=path_coords(graph, nodes),
        distance_m=path_length_m(graph, nodes),
        mode=mode,
    )
