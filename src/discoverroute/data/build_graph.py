"""Offline: download the Paris OSM extract and build the walk/bike routing graph.

Run once (cached for the Space):

    python -m discoverroute.data.build_graph

Produces ``data/paris_walk.graphml``. The graph is mode-agnostic: edges carry
length in metres; travel time is derived per mode at runtime from
``config.speed_ms`` so a single graph serves both walking and cycling. (Bikes on
the pedestrian network is a documented v1 approximation — see README.)
"""
from __future__ import annotations

import time

import osmnx as ox

from discoverroute import config


def build_walk_graph(place: str = config.PARIS_PLACE):
    """Download and return the Paris walking network as a networkx MultiDiGraph."""
    ox.settings.use_cache = True
    ox.settings.log_console = True
    print(f"[build_graph] downloading walk network for: {place!r}")
    t0 = time.time()
    graph = ox.graph_from_place(place, network_type="walk")
    print(
        f"[build_graph] downloaded {graph.number_of_nodes():,} nodes / "
        f"{graph.number_of_edges():,} edges in {time.time() - t0:.1f}s"
    )
    # Keep only the largest strongly connected component so every node is
    # reachable from every other — avoids "no path" failures on islands.
    graph = ox.truncate.largest_component(graph, strongly=True)
    print(
        f"[build_graph] largest strongly-connected component: "
        f"{graph.number_of_nodes():,} nodes / {graph.number_of_edges():,} edges"
    )
    return graph


def main() -> None:
    graph = build_walk_graph()
    config.GRAPH_WALK_PATH.parent.mkdir(parents=True, exist_ok=True)
    print(f"[build_graph] saving to {config.GRAPH_WALK_PATH}")
    ox.save_graphml(graph, config.GRAPH_WALK_PATH)
    print("[build_graph] done.")


if __name__ == "__main__":
    main()
