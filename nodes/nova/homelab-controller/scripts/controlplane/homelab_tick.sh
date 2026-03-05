#!/usr/bin/env bash
# P43 — Homelab Control Plane Tick
# Runs read-only inventory collection, sanitizes, and optionally pushes to GitHub
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
INVENTORY="$ROOT_DIR/inventory/inventory.yml"
PLAYBOOKS="$ROOT_DIR/playbooks"
ARTIFACTS="$ROOT_DIR/artifacts/controlplane"
TIMESTAMP=$(date +%Y-%m-%d)

echo "=============================================="
echo "  Homelab Control Plane Tick"
echo "  $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "=============================================="

# Parse args
MODE="${1:-quick}"  # quick or full
PUSH="${2:-no}"     # push or no

mkdir -p "$ARTIFACTS"

# Load secrets if available
SECRETS_ENV="$HOME/.config/homelab/secrets.env"
if [ -f "$SECRETS_ENV" ]; then
    echo "→ Loading secrets from $SECRETS_ENV"
    set -a; source "$SECRETS_ENV"; set +a
else
    echo "→ No secrets.env found (some inventories may be limited)"
fi

echo ""
echo "=== Phase 1: Preflight ==="
ansible-playbook -i "$INVENTORY" "$PLAYBOOKS/00_preflight.yml" 2>&1 || echo "⚠️  Some hosts unreachable (continuing)"

echo ""
echo "=== Phase 2: Node BIOS/Firmware ==="
ansible-playbook -i "$INVENTORY" "$PLAYBOOKS/35_inventory_bios.yml" 2>&1 || echo "⚠️  BIOS inventory partial"

if [ "$MODE" = "full" ]; then
    echo ""
    echo "=== Phase 3: OPNsense Inventory ==="
    ansible-playbook -i "$INVENTORY" "$PLAYBOOKS/10_inventory_opnsense.yml" 2>&1 || echo "⚠️  OPNsense inventory failed"

    echo ""
    echo "=== Phase 4: Proxmox Inventory ==="
    ansible-playbook -i "$INVENTORY" "$PLAYBOOKS/20_inventory_proxmox.yml" 2>&1 || echo "⚠️  Proxmox inventory partial"

    echo ""
    echo "=== Phase 5: Switch Inventory ==="
    ansible-playbook -i "$INVENTORY" "$PLAYBOOKS/30_inventory_switches.yml" 2>&1 || echo "⚠️  Switch inventory partial"
fi

echo ""
echo "=== Phase 6: Sanitize ==="
bash "$SCRIPT_DIR/sanitize.sh" "$ARTIFACTS"

echo ""
echo "=== Phase 7: Local Commit ==="
cd "$ROOT_DIR"
git add artifacts/controlplane/ 2>/dev/null || true
if ! git diff --cached --quiet 2>/dev/null; then
    git commit -m "inventory: controlplane tick $TIMESTAMP ($MODE)" 2>/dev/null || true
    echo "✅ Changes committed locally"
else
    echo "ℹ️  No changes to commit"
fi

if [ "$PUSH" = "push" ]; then
    echo ""
    echo "=== Phase 8: Push to GitHub ==="
    bash "$SCRIPT_DIR/git_push.sh"
fi

echo ""
echo "=============================================="
echo "  Tick complete: $MODE mode"
echo "  Artifacts: $ARTIFACTS"
echo "=============================================="
