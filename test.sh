#!/bin/bash
set -e
cd /Users/tristanleduc/Documents/Code_projects/discoverroute
source .venv/bin/activate
python -m pytest tests/ -v --tb=short
