#!/usr/bin/env bash
# D8 — DR Tick: wrapper for timer/scheduled execution
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."

NODE="${1:-}"
if [ -z "$NODE" ]; then
    NODE=$(hostname | tr '[:upper:]' '[:lower:]')
    for n in jasper nova mira orin; do
        if echo "$NODE" | grep -qi "$n"; then
            NODE="$n"
            break
        fi
    done
fi

echo "=== DR Tick: $NODE — $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

# Step 1: Preflight
echo "→ Preflight..."
python3 "$SCRIPT_DIR/dr_preflight.py" --node "$NODE" --allow-dirty || {
    echo "⚠️  Preflight failed — skipping drill"
    exit 0
}

# Step 2: Inventory
echo "→ Inventory..."
python3 "$SCRIPT_DIR/dr_backup_inventory.py" --node "$NODE"

# Step 3: Validate
echo "→ Validate..."
python3 "$SCRIPT_DIR/dr_validate.py" --node "$NODE" || true

# Step 4: Check if drill is due
POLICY="$ROOT_DIR/config/dr_policy.json"
DRILL_ENABLED=$(python3 -c "import json; print(json.load(open('$POLICY')).get('drill',{}).get('enabled', False))")
if [ "$DRILL_ENABLED" = "True" ]; then
    LAST_DRILL=$(find "$ROOT_DIR/artifacts/dr/" -name "drill_report_*.json" -printf '%T@\n' 2>/dev/null | sort -rn | head -1)
    NOW=$(date +%s)
    INTERVAL_SEC=$(python3 -c "import json; print(json.load(open('$POLICY')).get('drill',{}).get('interval_days', 7) * 86400)")

    if [ -z "$LAST_DRILL" ] || [ "$(echo "$NOW - ${LAST_DRILL%.*}" | bc)" -gt "$INTERVAL_SEC" ]; then
        echo "→ Drill is due — running..."
        python3 "$SCRIPT_DIR/dr_drill.py" --node "$NODE" || true
    else
        echo "→ Drill not due yet (last: $(date -d @${LAST_DRILL%.*} +%Y-%m-%d 2>/dev/null || echo 'recent'))"
    fi
else
    echo "→ Drill disabled in policy"
fi

echo "=== DR Tick complete ==="
