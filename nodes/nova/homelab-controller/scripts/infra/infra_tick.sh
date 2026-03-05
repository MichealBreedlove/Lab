#!/usr/bin/env bash
# P37 — Infrastructure Tick: inventory + exports + status
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."

echo "=== Infrastructure Tick — $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

echo "→ Collecting node inventory..."
python3 "$SCRIPT_DIR/infra_inventory.py"

echo ""
echo "→ Exporting Proxmox configs..."
python3 "$SCRIPT_DIR/proxmox_export.py" || echo "⚠️  Proxmox export failed (SSH access may be needed)"

echo ""
echo "→ Checking OPNsense backup..."
python3 "$SCRIPT_DIR/opnsense_backup.py"

echo ""
echo "→ Publishing infra status..."
python3 "$SCRIPT_DIR/infra_publish.py"

echo ""
echo "=== Infrastructure tick complete ==="
