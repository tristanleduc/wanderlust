"""Real graph travel-time matrix over a small set of anchor points.

Used to feed the orienteering solver *real* (not Euclidean) travel times so the
budget is enforced against the actual network. We only build the matrix over the
start, end, and a capped shortlist of top-scoring candidate POIs (a few dozen),
so the cost is a handful of cutoff-bounded Dijkstra runs, not all-pairs over 77k
nodes.
"""
from __future__ import annotations

import numpy as np
import osmnx as ox
from scipy.sparse.csgraph import dijkstra

from discoverroute import config
from discoverroute.routing import graph as g

INF = float("inf")


class TravelMatrix:
    """Pairwise shortest-path travel times among anchor points (by index)."""

    def __init__(self, points, nodes, dist_m, mode):
        self.points = points              # list[(lat, lon)] in matrix order
        self.nodes = nodes                # graph node id per anchor
        self.dist_m = dist_m              # NxN metres (INF if beyond cutoff)
        self.mode = mode
        self._speed = config.speed_ms(mode)
        self._index = {self._key(p): i for i, p in enumerate(points)}

    @staticmethod
    def _key(p):
        return (round(p[0], 7), round(p[1], 7))

    def time_fn(self):
        """A ``time_fn`` for orienteering.solve, looking up anchors by coordinate."""
        def fn(a, b):
            ia, ib = self._index[self._key(a)], self._index[self._key(b)]
            return self.dist_m[ia][ib] / self._speed
        return fn

    def direct_time_s(self, start_idx=0, end_idx=1):
        return self.dist_m[start_idx][end_idx] / self._speed

    def node_for(self, point) -> int:
        return self.nodes[self._index[self._key(point)]]


def build_matrix(graph, points, mode, cutoff_m) -> TravelMatrix:
    """Build a travel matrix over ``points`` (list of (lat, lon)).

    ``points[0]`` and ``points[1]`` are conventionally start and end. Distances
    come from one C-speed multi-source SciPy Dijkstra bounded by ``cutoff_m``;
    pairs farther than the cutoff stay INF (treated as infeasible by the solver).
    """
    lats = np.array([p[0] for p in points])
    lons = np.array([p[1] for p in points])
    nodes = ox.distance.nearest_nodes(graph, X=lons, Y=lats)
    nodes = [int(n) for n in np.atleast_1d(nodes)]

    csr, _, idx = g.graph_csr()
    anchor_idx = [idx[n] for n in nodes]
    # one call computes all sources -> all nodes, bounded by the cutoff
    dmat = dijkstra(csr, directed=True, indices=anchor_idx, limit=cutoff_m)
    n = len(points)
    dist = [[0.0 if i == j else float(dmat[i][anchor_idx[j]])
             for j in range(n)] for i in range(n)]
    return TravelMatrix(points, nodes, dist, mode)
