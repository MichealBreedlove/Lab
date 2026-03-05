#!/usr/bin/env bash
# P39 — Portfolio Tick: render + secretscan + status
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."

echo "=== Portfolio Tick — $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
echo "→ Rendering portfolio docs..."
python3 "$SCRIPT_DIR/portfolio_render.py"
echo ""
echo "→ Secret scan..."
python3 "$ROOT_DIR/scripts/sec/sec_secretscan.py" || true
echo ""
echo "→ Publishing status..."
python3 "$SCRIPT_DIR/portfolio_publish.py"
echo ""
echo "=== Portfolio tick complete ==="
