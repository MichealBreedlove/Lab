#!/usr/bin/env bash
# P43 — Push sanitized artifacts to MichealBreedlove/Lab
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
ARTIFACTS="$ROOT_DIR/artifacts/controlplane"
LAB_REPO="$HOME/Lab"
TIMESTAMP=$(date +%Y-%m-%d)

echo "-> Syncing artifacts to Lab repo..."

if [ ! -d "$LAB_REPO/.git" ]; then
    echo "[ERROR] Lab repo not found at $LAB_REPO"
    echo "   Clone it: git clone https://github.com/MichealBreedlove/Lab.git ~/Lab"
    exit 1
fi

# Sync artifacts to Lab repo structure
sync_dir() {
    local src="$1"
    local dst="$2"
    if [ -d "$src" ]; then
        mkdir -p "$LAB_REPO/$dst"
        rsync -av --delete "$src/" "$LAB_REPO/$dst/" 2>/dev/null || cp -r "$src/"* "$LAB_REPO/$dst/"
        echo "  [OK] $dst"
    fi
}

# Map controlplane artifacts to Lab repo paths
sync_dir "$ARTIFACTS/opnsense" "network/opnsense/inventory"
sync_dir "$ARTIFACTS/proxmox" "proxmox"
sync_dir "$ARTIFACTS/switches" "network/switches"
sync_dir "$ARTIFACTS/bios" "bios"

# Commit and push
cd "$LAB_REPO"
git add -A 2>/dev/null || true

if ! git diff --cached --quiet 2>/dev/null; then
    git commit -m "inventory: controlplane sync $TIMESTAMP" 2>/dev/null
    echo "[OK] Committed to Lab repo"

    if git push origin main 2>/dev/null; then
        echo "[OK] Pushed to GitHub"
    else
        echo "[WARN] Push failed (no credentials or network issue)"
        echo "   Run from GamingPC: cd ~/Lab && git pull && git push"
    fi
else
    echo "[INFO] No changes to push"
fi
