#!/usr/bin/env bash
# P42 — Release Tag: create v1.1.0 git tag
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT_DIR"

VERSION="v1.1.0"

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
    git tag -a "$VERSION" -m "OpenClaw Homelab Control Plane $VERSION — Platform Operations & Governance

Builds on v1.0 with 6 new subsystems (P36-P41):

New in v1.1:
- Observability stack (Prometheus, Grafana, Loki, Alertmanager, Event Bus)
- Infrastructure control plane (inventory, Proxmox/OPNsense backup)
- Security hygiene (baseline auditing, secret scanning, repo guard)
- Recruiter export pack (auto-generated portfolio docs + badges)
- Continuous verification (synthetic probes, canaries, policy gates)
- Hardening + supply chain (SBOM, provenance, script hygiene)

Stats:
- 120+ acceptance tests across 12 test suites
- 16+ CLI subcommands
- 12+ dashboard panels with auto-refresh
- Zero third-party Python dependencies

Nodes: Jasper (GPU gateway), Nova (controller), Mira (worker), Orin (compute)
Infrastructure: Proxmox cluster, OPNsense, TrueNAS, UniFi"

    echo "✅ Tag $VERSION created"
    echo ""
    echo "To push: git push origin $VERSION"
else
    echo "ℹ️  Dry-run. Would create tag: $VERSION"
    echo "  Run with --apply to create the tag"
fi
