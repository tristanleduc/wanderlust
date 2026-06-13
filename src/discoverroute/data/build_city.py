"""Pre-bake a walkable *city core* (graph + POIs) for offline routing.

Paris ships full-city; additional cities are baked as a bounded core (a box
around the centre) so the data stays small and the build is quick, while still
covering the walkable, demo-worthy heart of the city. Running this writes
``data/cities/<slug>_walk.graphml`` + ``data/cities/<slug>_pois.parquet`` so the
city routes **fully offline** at request time — no live OSM calls, preserving the
"Off the Grid" badge while still being multi-city.

    python -m discoverroute.data.build_city london
    python -m discoverroute.data.build_city          # all cities in config.CITIES
"""
from __future__ import annotations

import json
import math
import sys
import time
from datetime import datetime, timezone

import osmnx as ox

from discoverroute import config
from discoverroute.routing.area import _fetch_pois  # reuse the tested POI fetch


def _bbox_from_center(center, radius_m):
    """(left, bottom, right, top) = (W, S, E, N) box around a centre point."""
    lat, lon = center
    dlat = radius_m / 110_540.0
    dlon = radius_m / (111_320.0 * max(0.1, math.cos(math.radians(lat))))
    return (lon - dlon, lat - dlat, lon + dlon, lat + dlat)


def build_city(slug: str) -> None:
    spec = config.CITIES.get(slug)
    if spec is None:
        raise SystemExit(f"Unknown city {slug!r}. Known: {', '.join(config.CITIES)}")
    label = spec["label"]
    bbox = _bbox_from_center(spec["center"], spec["radius_m"])

    ox.settings.use_cache = True
    ox.settings.log_console = False
    ox.settings.requests_timeout = 180

    config.CITY_DATA_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    print(f"[build_city] {label}: downloading walk graph for bbox {bbox}")
    graph = ox.graph_from_bbox(bbox, network_type="walk")
    graph = ox.truncate.largest_component(graph, strongly=True)
    gpath = config.city_graph_path(slug)
    ox.save_graphml(graph, gpath)
    print(f"[build_city] {label}: {graph.number_of_nodes():,} nodes -> {gpath.name}")

    df = _fetch_pois(bbox)
    if not len(df):
        raise SystemExit(f"[build_city] {label}: no POIs found — aborting.")
    ppath = config.city_pois_path(slug)
    df.to_parquet(ppath, index=False)
    print(f"[build_city] {label}: {len(df):,} POIs -> {ppath.name} "
          f"(by category:\n{df['category'].value_counts().to_string()})")

    # Per-city provenance, appended to the cities manifest.
    manifest = {}
    if config.CITIES_MANIFEST_PATH.exists():
        manifest = json.loads(config.CITIES_MANIFEST_PATH.read_text("utf-8"))
    manifest[slug] = {
        "label": label,
        "center": list(spec["center"]),
        "bbox": list(bbox),
        "tz": spec["tz"],
        "poi_count": int(len(df)),
        "build_date": datetime.now(timezone.utc).date().isoformat(),
        "source": "OpenStreetMap", "license": "ODbL — © OpenStreetMap contributors",
    }
    config.CITIES_MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", "utf-8")
    print(f"[build_city] {label}: done in {time.time() - t0:.0f}s")


def main() -> None:
    slugs = sys.argv[1:] or list(config.CITIES)
    for s in slugs:
        build_city(s)


if __name__ == "__main__":
    main()
