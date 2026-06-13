"""Offline: extract Paris POIs from OSM, compute features + confidence, cache.

Run once (after build_graph):

    python -m discoverroute.data.build_pois

Produces ``data/paris_pois.parquet`` with one row per candidate POI:
  osm_type, osm_id, name, lat, lon, category, greenness, quietness, confidence, n_tags

Greenness/quietness are category priors; confidence is tag-richness (see taxonomy).
"""
from __future__ import annotations

import time

import osmnx as ox
import pandas as pd

from discoverroute import config
from discoverroute.data import taxonomy

# A combined all-keys query over the whole city overruns the public Overpass
# server's time/memory limits. Fetch one tag key at a time (much lighter) and
# concatenate; dedupe on the OSM element id afterwards.
_REQUEST_TIMEOUT = 300

# Non-tag columns present in the features GeoDataFrame we don't treat as tags.
_NON_TAG_COLS = {"geometry", "nodes", "ways", "members"}


def _row_tags(row: pd.Series) -> dict:
    """Build a flat {key: value} tag dict from a features GeoDataFrame row."""
    return {
        k: v
        for k, v in row.items()
        if k not in _NON_TAG_COLS and pd.notna(v)
    }


def _point_of(geom):
    """Representative (lat, lon) for a POI geometry (point or polygon)."""
    if geom is None:
        return None
    if geom.geom_type == "Point":
        return geom.y, geom.x
    p = geom.representative_point()
    return p.y, p.x


def _download_features(place: str):
    """Fetch features one tag key at a time and concatenate (dedupe by id)."""
    frames = []
    for key in taxonomy.OSM_QUERY_TAGS:
        t0 = time.time()
        try:
            part = ox.features_from_place(place, {key: True})
        except Exception as exc:  # noqa: BLE001
            print(f"[build_pois]   key {key!r} FAILED: {exc}")
            continue
        print(f"[build_pois]   key {key!r}: {len(part):,} features "
              f"in {time.time() - t0:.1f}s")
        frames.append(part)
    if not frames:
        raise RuntimeError("All Overpass key queries failed.")
    gdf = pd.concat(frames)
    gdf = gdf[~gdf.index.duplicated(keep="first")]
    return gdf


def build_pois(place: str = config.PARIS_PLACE) -> pd.DataFrame:
    ox.settings.use_cache = True
    ox.settings.log_console = True
    ox.settings.requests_timeout = _REQUEST_TIMEOUT
    print(f"[build_pois] downloading features for: {place!r}")
    t0 = time.time()
    gdf = _download_features(place)
    print(f"[build_pois] {len(gdf):,} unique raw features in {time.time() - t0:.1f}s")

    records = []
    skipped = 0
    for idx, row in gdf.iterrows():
        tags = _row_tags(row)
        category = taxonomy.classify(tags)
        if category is None:
            skipped += 1
            continue
        pt = _point_of(row.geometry)
        if pt is None or not config.in_paris(pt[0], pt[1]):
            skipped += 1
            continue
        osm_type, osm_id = (idx if isinstance(idx, tuple) else ("node", idx))
        name = tags.get("name")
        hours = tags.get("opening_hours")
        records.append(
            {
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
            }
        )

    df = pd.DataFrame.from_records(records)
    print(
        f"[build_pois] kept {len(df):,} POIs ({skipped:,} skipped). "
        f"By category:\n{df['category'].value_counts().to_string()}"
    )
    return df


def main() -> None:
    import json
    from datetime import datetime, timezone

    df = build_pois()
    config.POIS_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(config.POIS_PATH, index=False)
    print(f"[build_pois] saved {len(df):,} POIs to {config.POIS_PATH}")

    # Provenance manifest so the app can show an honest "data as of <date>" line.
    n = max(1, len(df))
    hours = int(df["opening_hours"].notna().sum())
    manifest = {
        "source": "OpenStreetMap",
        "license": "ODbL — © OpenStreetMap contributors",
        "city": "Paris",
        "build_date": datetime.now(timezone.utc).date().isoformat(),
        "poi_count": int(len(df)),
        "opening_hours_coverage_pct": round(hours / n * 100, 1),
    }
    config.DATA_MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"[build_pois] wrote manifest {config.DATA_MANIFEST_PATH}")


if __name__ == "__main__":
    main()
