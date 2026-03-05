#!/usr/bin/env bash
# incident_tick.sh — Pipeline wrapper: check triggers, render, copy to services
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."

echo "=== Incident tick @ $(date -Iseconds) ==="

# Step 1: Run trigger check
cd "$SCRIPT_DIR"
python3 incident_manager.py tick

# Step 2: Render latest incident artifacts
LATEST=$(ls -1t "$ROOT_DIR/artifacts/incidents"/INC-*.json 2>/dev/null | head -1)
if [ -n "$LATEST" ]; then
    INC_ID=$(basename "$LATEST" .json)
    python3 incident_render.py "$INC_ID"

    # Step 3: Copy to services/openclaw/incidents/
    SVC_DIR="$ROOT_DIR/../../services/openclaw/incidents"
    mkdir -p "$SVC_DIR"
    cp "$ROOT_DIR/artifacts/incidents/$INC_ID.json" "$SVC_DIR/latest_incident.json" 2>/dev/null || true
    [ -f "$ROOT_DIR/artifacts/incidents/postmortem_$INC_ID.md" ] && \
        cp "$ROOT_DIR/artifacts/incidents/postmortem_$INC_ID.md" "$SVC_DIR/latest_postmortem.md" 2>/dev/null || true
fi

echo "=== Incident tick complete ==="
