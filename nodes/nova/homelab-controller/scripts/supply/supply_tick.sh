#!/usr/bin/env bash
# P41 — Supply Chain Tick: SBOM + provenance + hardening + publish
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."

echo "=== Supply Chain Tick — $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
echo "→ Generating SBOM..."
python3 "$SCRIPT_DIR/supply_sbom.py"
echo ""
echo "→ Recording provenance..."
python3 "$SCRIPT_DIR/supply_provenance.py"
echo ""
echo "→ Running hardening checks..."
python3 "$SCRIPT_DIR/supply_harden.py"
echo ""
echo "→ Secret scan..."
python3 "$ROOT_DIR/scripts/sec/sec_secretscan.py" || true
echo ""
echo "→ Publishing status..."
python3 "$SCRIPT_DIR/supply_publish.py"
echo ""
echo "=== Supply chain tick complete ==="
