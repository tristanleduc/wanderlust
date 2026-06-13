#!/usr/bin/env python
"""Quick test runner to check all imports and basic functionality."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("=" * 60)
print("IMPORT CHECK")
print("=" * 60)

# Test critical imports
try:
    from discoverroute import config
    print("✓ discoverroute.config")
    print(f"  - Graph path exists: {config.GRAPH_WALK_PATH.exists()}")
    print(f"  - POI path exists: {config.POIS_PATH.exists()}")
except Exception as e:
    print(f"✗ discoverroute.config: {e}")
    import traceback
    traceback.print_exc()

try:
    from discoverroute.routing import graph
    print("✓ discoverroute.routing.graph")
except Exception as e:
    print(f"✗ discoverroute.routing.graph: {e}")
    import traceback
    traceback.print_exc()

try:
    from discoverroute.routing import pois
    print("✓ discoverroute.routing.pois")
except Exception as e:
    print(f"✗ discoverroute.routing.pois: {e}")
    import traceback
    traceback.print_exc()

try:
    from discoverroute.pipeline import plan_route
    print("✓ discoverroute.pipeline")
except Exception as e:
    print(f"✗ discoverroute.pipeline: {e}")
    import traceback
    traceback.print_exc()

try:
    from discoverroute.ui import design, map
    print("✓ discoverroute.ui")
except Exception as e:
    print(f"✗ discoverroute.ui: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 60)
print("DATA LOADING TEST (10-15 sec expected)")
print("=" * 60)

try:
    from discoverroute.routing.graph import load_graph_walk
    import time
    print("Loading graph...")
    start = time.time()
    g = load_graph_walk()
    elapsed = time.time() - start
    print(f"✓ Graph loaded in {elapsed:.1f}s")
    print(f"  - Nodes: {g.number_of_nodes()}")
    print(f"  - Edges: {g.number_of_edges()}")
except Exception as e:
    print(f"✗ Graph load failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from discoverroute.routing.pois import load_pois_table
    print("Loading POIs...")
    start = time.time()
    pois_df = load_pois_table()
    elapsed = time.time() - start
    print(f"✓ POIs loaded in {elapsed:.1f}s")
    print(f"  - POI count: {len(pois_df)}")
    print(f"  - Columns: {list(pois_df.columns)}")
except Exception as e:
    print(f"✗ POI load failed: {e}")
    import traceback
    traceback.print_exc()

try:
    from discoverroute.interpret.embed import get_embedder
    print("Loading embedding model...")
    start = time.time()
    embedder = get_embedder()
    elapsed = time.time() - start
    print(f"✓ Embedder loaded in {elapsed:.1f}s")
except Exception as e:
    print(f"✗ Embedder load failed: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 60)
print("APP IMPORT TEST")
print("=" * 60)

try:
    import app
    print("✓ app.py imported successfully")
except Exception as e:
    print(f"✗ app.py import failed: {e}")
    import traceback
    traceback.print_exc()

print()
print("=" * 60)
print("PYTEST RUN")
print("=" * 60)

import subprocess
result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
    cwd=Path(__file__).parent,
)
sys.exit(result.returncode)
