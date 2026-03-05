#!/usr/bin/env bash
# P36 — Observability Tick: refresh status, rotate logs, publish
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Observability Tick — $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

echo "→ Publishing status..."
python3 "$SCRIPT_DIR/obs_publish.py"

echo ""
echo "→ Writing tick event..."
python3 "$SCRIPT_DIR/obs_eventbus.py" write --type obs.stack.up --severity info --node nova --component observability --message "Observability tick completed"

echo ""
echo "=== Observability tick complete ==="
