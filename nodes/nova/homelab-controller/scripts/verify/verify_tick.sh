#!/usr/bin/env bash
# P40 — Verification Tick: synthetic + canary + gates + publish
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Verification Tick — $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
echo "→ Synthetic checks..."
python3 "$SCRIPT_DIR/verify_synthetic.py" || true
echo ""
echo "→ Canary checks..."
python3 "$SCRIPT_DIR/verify_canary.py" || true
echo ""
echo "→ Policy gates..."
python3 "$SCRIPT_DIR/verify_gates.py"
echo ""
echo "→ Publishing status..."
python3 "$SCRIPT_DIR/verify_publish.py"
echo ""
echo "=== Verification tick complete ==="
