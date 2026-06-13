#!/bin/bash
cd /Users/tristanleduc/Documents/Code_projects/discoverroute
export PYTHONPATH="/Users/tristanleduc/Documents/Code_projects/discoverroute/src:$PYTHONPATH"

# Run import check first
.venv/bin/python << 'EOFPYTHON'
import sys
sys.path.insert(0, 'src')
print("=" * 60)
print("IMPORT CHECK")
print("=" * 60)

try:
    from discoverroute import config
    print("✓ discoverroute.config")
    print(f"  Graph: {config.GRAPH_WALK_PATH.exists()}")
    print(f"  POIs: {config.POIS_PATH.exists()}")
except Exception as e:
    print(f"✗ {e}")
    import traceback
    traceback.print_exc()

EOFPYTHON

# Run pytest
echo ""
echo "=" * 60
echo "PYTEST TESTS"
echo "=" * 60
.venv/bin/python -m pytest tests/ -v --tb=short
