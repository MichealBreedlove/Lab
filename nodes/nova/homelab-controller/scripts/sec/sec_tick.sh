#!/usr/bin/env bash
# P38 — Security Tick: audit + secretscan + publish status
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."

echo "=== Security Tick — $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
echo "→ Running baseline audit..."
python3 "$SCRIPT_DIR/sec_baseline_audit.py" || true
echo ""
echo "→ Running secret scan..."
python3 "$SCRIPT_DIR/sec_secretscan.py"
echo ""
echo "→ Publishing security status..."
python3 "$SCRIPT_DIR/sec_publish.py"
echo ""
echo "=== Security tick complete ==="
