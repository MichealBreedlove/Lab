#!/usr/bin/env bash
# P36 — Observability Stack Install (Nova only)
# Installs Docker + Compose if not present, creates stack directories
set -euo pipefail

OBS_DIR="${HOME}/obs-stack"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== Observability Stack Install — $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

# Check if running on Linux
if [[ "$(uname)" != "Linux" ]]; then
    echo "❌ This script is for Linux (Nova) only"
    exit 1
fi

# Step 1: Check/install Docker
if command -v docker &>/dev/null; then
    echo "✅ Docker already installed: $(docker --version)"
else
    echo "→ Installing Docker..."
    if [ "${1:-}" = "--apply" ]; then
        curl -fsSL https://get.docker.com | sh
        sudo usermod -aG docker "$USER"
        echo "✅ Docker installed. Log out/in for group change."
    else
        echo "ℹ️  Would install Docker. Pass --apply to execute."
    fi
fi

# Step 2: Check/install Docker Compose
if command -v docker-compose &>/dev/null || docker compose version &>/dev/null 2>&1; then
    echo "✅ Docker Compose available"
else
    echo "→ Installing Docker Compose plugin..."
    if [ "${1:-}" = "--apply" ]; then
        sudo apt-get install -y docker-compose-plugin 2>/dev/null || pip3 install docker-compose
        echo "✅ Docker Compose installed"
    else
        echo "ℹ️  Would install Docker Compose. Pass --apply to execute."
    fi
fi

# Step 3: Create stack directories
echo "→ Creating stack directories at $OBS_DIR..."
mkdir -p "$OBS_DIR"/{prometheus,grafana/{provisioning/datasources,provisioning/dashboards,dashboards},alertmanager,loki,promtail}
echo "✅ Directories created"

# Step 4: Copy compose + configs
echo "→ Copying stack configs..."
cp -n "$SCRIPT_DIR/obs_compose.yml" "$OBS_DIR/docker-compose.yml" 2>/dev/null || true
cp -n "$SCRIPT_DIR/obs_scrape.yml" "$OBS_DIR/prometheus/prometheus.yml" 2>/dev/null || true
cp -n "$SCRIPT_DIR/obs_rules.yml" "$OBS_DIR/prometheus/rules.yml" 2>/dev/null || true
echo "✅ Configs copied (existing files preserved)"

echo ""
echo "=== Install complete ==="
echo "Next: cd $OBS_DIR && docker compose up -d"
