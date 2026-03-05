#!/usr/bin/env bash
# portfolio_tick.sh — Pipeline wrapper: redact → build → publish
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
LAB_ROOT="$ROOT_DIR/../../.."

echo "=== Portfolio tick @ $(date -Iseconds) ==="

cd "$SCRIPT_DIR"

# Step 1: Build site content
echo "[1/3] Building site..."
python3 portfolio_build.py

# Step 2: Redact any secrets in site output
echo "[2/3] Redacting..."
python3 portfolio_redact.py "$LAB_ROOT/site"

# Step 3: Publish
echo "[3/3] Publishing..."
python3 portfolio_publish.py

echo "=== Portfolio tick complete ==="
