#!/usr/bin/env bash
# lab-backup.sh — Collect node state, sanitize, commit, push
# Run on each Linux node (nova/mira/orin)
# Usage: bash lab-backup.sh
set -euo pipefail

HOSTNAME=$(hostname)
REPO_DIR="$HOME/Lab"
NODE_DIR="$REPO_DIR/nodes/$HOSTNAME"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATE=$(date +%Y-%m-%d)
TIME=$(date +%H:%M)

echo "=== Lab backup: $HOSTNAME @ $DATE $TIME ==="

# Ensure repo is up to date
cd "$REPO_DIR"
git pull --rebase --quiet 2>/dev/null || true

# Create node directories
mkdir -p "$NODE_DIR"/{openclaw,system,logs}

# --- Collect system info ---
echo "Collecting system info..."
{
    echo "# System State — $HOSTNAME"
    echo "Generated: $DATE $TIME"
    echo ""
    echo "## Kernel"
    uname -a
    echo ""
    echo "## Uptime"
    uptime
    echo ""
    echo "## Disk"
    df -h
    echo ""
    echo "## Memory"
    free -h
    echo ""
    echo "## Network"
    ip -br a
    echo ""
    echo "## Listening Ports"
    ss -ltnp 2>/dev/null | head -30 || echo "(requires root for full output)"
} > "$NODE_DIR/system/state.md" 2>/dev/null || true

# --- Collect OpenClaw info ---
echo "Collecting OpenClaw info..."
if command -v openclaw &>/dev/null; then
    {
        echo "# OpenClaw State — $HOSTNAME"
        echo "Generated: $DATE $TIME"
        echo ""
        echo "## Version"
        openclaw --version 2>/dev/null || echo "N/A"
        echo ""
        echo "## Service Status"
        sudo systemctl status openclaw-node.service --no-pager -l 2>&1 || \
            echo "(service not running or not installed)"
    } > "$NODE_DIR/openclaw/status.md" 2>/dev/null || true
fi

# --- Collect enabled services list ---
systemctl list-unit-files --state=enabled --no-pager 2>/dev/null \
    > "$NODE_DIR/system/enabled_services.txt" || true

# --- Sanitize ---
echo "Sanitizing..."
bash "$SCRIPT_DIR/lab-sanitize.sh" "$NODE_DIR"

# --- Commit & Push ---
echo "Committing..."
cd "$REPO_DIR"
git add "nodes/$HOSTNAME/" 2>/dev/null || true
git add -A 2>/dev/null || true

if git diff --cached --quiet; then
    echo "No changes to commit."
else
    git commit -m "node:$HOSTNAME backup $DATE $TIME" --quiet
    echo "Pushing..."
    git push --quiet 2>/dev/null || echo "Push failed (will retry next run)"
fi

echo "=== Backup complete: $HOSTNAME ==="
