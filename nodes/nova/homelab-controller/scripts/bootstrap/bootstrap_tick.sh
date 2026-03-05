#!/usr/bin/env bash
# P31 — Bootstrap Tick: orchestrate full bootstrap pipeline for a node
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."

NODE="${1:?Usage: bootstrap_tick.sh <node_name>}"

echo "=== Bootstrap Tick: $NODE — $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

# Step 1: Preflight
echo "→ Step 1: Preflight..."
if ! python3 "$SCRIPT_DIR/bootstrap_preflight.py" --node "$NODE"; then
    echo "❌ Preflight failed — cannot proceed"
    exit 1
fi

# Step 2: Install (dry-run first)
echo "→ Step 2: Install (dry-run)..."
python3 "$SCRIPT_DIR/bootstrap_install.py" --node "$NODE" --dry-run

echo ""
echo "Review the install plan above."
echo "To apply: python3 $SCRIPT_DIR/bootstrap_install.py --node $NODE --apply"
echo ""

# Check if --apply was passed
if [ "${2:-}" = "--apply" ]; then
    echo "→ Step 2b: Install (applying)..."
    python3 "$SCRIPT_DIR/bootstrap_install.py" --node "$NODE" --apply

    echo "→ Step 3: Configure..."
    python3 "$SCRIPT_DIR/bootstrap_configure.py" --node "$NODE" --apply

    echo "→ Step 4: Register..."
    python3 "$SCRIPT_DIR/bootstrap_register.py" --node "$NODE" --apply

    echo "→ Step 5: Validate..."
    python3 "$SCRIPT_DIR/bootstrap_validate.py" --node "$NODE"

    echo ""
    echo "=== Bootstrap complete for $NODE ==="
else
    echo "ℹ️  Dry-run complete. Pass --apply to execute."
fi
