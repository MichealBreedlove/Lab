#!/usr/bin/env bash
# P34 — AIOps Tick: anomaly → correlate → analyze → report
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== AIOps Tick — $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

echo "→ Anomaly detection..."
python3 "$SCRIPT_DIR/aiops_anomaly.py"

echo ""
echo "→ Incident correlation..."
python3 "$SCRIPT_DIR/aiops_correlate.py"

echo ""
echo "→ AI analysis..."
python3 "$SCRIPT_DIR/aiops_analyze.py" --no-llm

echo ""
echo "→ Generating report..."
python3 "$SCRIPT_DIR/aiops_report.py"

echo ""
echo "=== AIOps tick complete ==="
