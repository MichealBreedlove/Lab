#!/usr/bin/env bash
# P35 — Release Tag: create v1.0.0 git tag
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

VERSION="v1.0.0"

echo "=== Release Tag: $VERSION ==="

# Pre-flight: audit
echo "→ Running release audit..."
python3 scripts/release/release_audit.py
if [ $? -ne 0 ]; then
    echo "❌ Audit failed — fix issues before tagging"
    exit 1
fi

# Check for existing tag
if git tag -l "$VERSION" | grep -q "$VERSION"; then
    echo "⚠️  Tag $VERSION already exists"
    echo "  To retag: git tag -d $VERSION && git push origin :refs/tags/$VERSION"
    exit 0
fi

# Check for clean working tree
if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  Working tree not clean. Commit changes first."
    git status --short
    exit 1
fi

# Create tag
if [ "${1:-}" = "--apply" ]; then
    git tag -a "$VERSION" -m "OpenClaw Homelab Control Plane $VERSION

Autonomous infrastructure platform — P1 through P35 complete.

Features:
- SLO monitoring with error budget burn rates
- Chaos testing engine
- One-command disaster recovery with drill validation
- Zero-touch node bootstrap (3 profiles, 4 nodes)
- Autonomous capacity management with forecasting
- Self-documenting architecture with Mermaid diagrams
- AI operations layer (anomaly detection, LLM analysis)
- Supervised mode with break-glass for destructive ops

Nodes: Jasper (GPU gateway), Nova (controller), Mira (worker), Orin (compute)
Infrastructure: Proxmox cluster, OPNsense, TrueNAS, UniFi"

    echo "✅ Tag $VERSION created"
    echo ""
    echo "To push: git push origin $VERSION"
else
    echo "ℹ️  Dry-run. Would create tag: $VERSION"
    echo "  Run with --apply to create the tag"
fi
