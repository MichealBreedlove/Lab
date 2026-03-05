#!/usr/bin/env bash
# P32 — Capacity Tick: collect → forecast → recommend → export dashboard
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Capacity Tick — $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

echo "→ Collecting metrics..."
python3 "$SCRIPT_DIR/capacity_collect.py"

echo ""
echo "→ Running forecast..."
python3 "$SCRIPT_DIR/capacity_forecast.py"

echo ""
echo "→ Generating recommendations..."
python3 "$SCRIPT_DIR/capacity_recommend.py"

echo ""
echo "→ Exporting to dashboard..."
python3 "$SCRIPT_DIR/capacity_dashboard_export.py"

echo ""
echo "=== Capacity tick complete ==="
