#!/usr/bin/env python3
"""P35 — Release Build Docs: generate release notes, restore guide, and system architecture."""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASE_DIR = ROOT / "release" / "v1.0"
DOCS_DIR = ROOT / "docs"


def get_git_tag_count():
    try:
        r = subprocess.run(["git", "-C", str(ROOT), "tag", "-l"], capture_output=True, text=True, timeout=10)
        return len([t for t in r.stdout.strip().splitlines() if t.strip()])
    except Exception:
        return 0


def get_commit_count():
    try:
        r = subprocess.run(["git", "-C", str(ROOT), "rev-list", "--count", "HEAD"], capture_output=True, text=True, timeout=10)
        return int(r.stdout.strip())
    except Exception:
        return 0


def generate_release_notes():
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    date_str = time.strftime("%Y-%m-%d")
    commits = get_commit_count()

    content = f"""# Release Notes — v1.0.0

**Release Date:** {date_str}
**Commits:** {commits}
**Status:** Production-ready homelab control plane

## Summary

OpenClaw Homelab Control Plane v1.0.0 — a fully autonomous infrastructure platform
managing a 4-node cluster with SLO monitoring, chaos testing, disaster recovery,
capacity management, AI-powered operations, and self-documenting architecture.

## Priorities Completed (P1–P35)

### Core Infrastructure (P1–P10)
- Per-node configuration segregation
- Backup automation with systemd timers
- CI secret scanning via GitHub Actions
- GitHub Pages documentation
- Snapshot pipeline

### Reliability (P11–P20)
- SLO monitoring with error budget burn rates
- Chaos testing engine
- Gatekeeper (approval gate for destructive ops)
- Incident memory and postmortem tracking
- Planner (autonomous task scheduling)

### Operations (P21–P30)
- Security telemetry collection
- Topology and services graph
- Portfolio publisher
- One-command disaster recovery
- DR drill with MTTR tracking
- Dashboard with SLO, incident, DR, bootstrap, capacity panels

### Advanced (P31–P35)
- Zero-touch node bootstrap (3 profiles, 4 nodes)
- Autonomous capacity manager (collection, forecasting, recommendations)
- Self-documenting architecture (topology, services, dependencies, diagrams)
- AI operations layer (anomaly detection, incident correlation, LLM analysis)
- System freeze and v1.0 release

## Architecture

- **Jasper** (i9-13900K, RTX 4090, 64GB) — AI gateway + LLM inference
- **Nova** (N305, 32GB DDR5) — Controller + orchestrator
- **Mira** (i7-2600K, 16GB) — Worker node
- **Orin** (R630, Dual Xeon, 16GB ECC) — Compute node
- **Infrastructure**: Proxmox cluster, OPNsense, TrueNAS, UniFi

## CLI Reference

```
oc dr status|preflight|restore|validate|drill|tick|test
oc bootstrap node|status|validate|test
oc capacity collect|forecast|recommend|tick|test
oc docs generate|topology|services|deps|changelog|diagrams|portfolio|test
oc aiops anomaly|correlate|analyze|report|tick|test
oc release audit|docs|package|test
oc test p30|p31|p32|p33|p34|p35|all
```

## Known Limitations

- Windows nodes (Jasper) require manual bootstrap steps
- LLM analysis requires Ollama running on Jasper
- Live service scanning requires SSH access from Nova
- Capacity collection is Linux-only (Windows metrics via separate tooling)

## Security

- All configs scanned for secrets before commit
- Break-glass token required for destructive DR operations
- Portfolio exports automatically redact tokens, passwords, and private keys
- Supervised mode by default — no autonomous destructive actions
"""

    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    (RELEASE_DIR / "RELEASE_NOTES.md").write_text(content)
    return {"file": "release/v1.0/RELEASE_NOTES.md"}


def generate_restore_guide():
    content = """# Restore Guide — v1.0.0

## Quick Restore

```bash
# From Nova controller
oc dr preflight
oc dr restore --node <name> --dry-run
oc dr restore --node <name> --apply
oc dr validate --node <name>
```

## Full Cluster Recovery

### Step 1: Verify backup freshness
```bash
oc dr status
```

### Step 2: Restore controller (Nova) first
```bash
oc dr restore --node nova --apply
oc dr validate --node nova
```

### Step 3: Restore workers
```bash
oc dr restore --node mira --apply
oc dr restore --node orin --apply
```

### Step 4: Validate cluster
```bash
oc dr validate --node nova
oc dr validate --node mira
oc dr validate --node orin
```

### Step 5: Run DR drill to confirm
```bash
oc dr drill
```

## Bootstrap a New Node

```bash
oc bootstrap node <name> --apply
oc bootstrap validate --node <name>
```

## Emergency: Break-Glass Restore

For autonomous restore when operator is unavailable:

```bash
# Generate break-glass token (valid 30 minutes)
echo $(date +%s) > config/break_glass.token
oc dr restore --node <name> --autonomous
```

## Contacts

- **Repository**: https://github.com/MichealBreedlove/Lab
- **DR Runbook**: docs/dr/DR_RUNBOOK.md
- **Bootstrap Runbook**: docs/bootstrap/BOOTSTRAP_RUNBOOK.md
"""

    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    (RELEASE_DIR / "RESTORE_GUIDE.md").write_text(content)
    return {"file": "release/v1.0/RESTORE_GUIDE.md"}


def generate_system_architecture():
    content = """# System Architecture — v1.0.0

## Overview

The OpenClaw Homelab Control Plane is an autonomous infrastructure management system
built on a 4-node cluster. It monitors, tests, recovers, optimizes, and documents
itself with minimal operator intervention.

## Node Architecture

| Node | IP | Role | Hardware |
|------|-----|------|----------|
| Jasper | 10.1.1.150 | AI Gateway | i9-13900K, RTX 4090, 64GB |
| Nova | 10.1.1.21 | Controller | N305, 32GB DDR5 |
| Mira | 10.1.1.22 | Worker | i7-2600K, 16GB |
| Orin | 10.1.1.23 | Worker | R630, Dual Xeon, 16GB ECC |

## Subsystem Map

| Subsystem | Config | Scripts | CLI |
|-----------|--------|---------|-----|
| Disaster Recovery | dr_policy.json | scripts/dr/ | oc dr |
| Node Bootstrap | bootstrap_policy.json | scripts/bootstrap/ | oc bootstrap |
| Capacity Manager | capacity_policy.json | scripts/capacity/ | oc capacity |
| Self-Documenting | docs_policy.json | scripts/docs/ | oc docs |
| AI Operations | aiops_policy.json | scripts/aiops/ | oc aiops |
| Release | — | scripts/release/ | oc release |

## Data Flow

1. **Collection**: Metrics gathered via SSH from all Linux nodes
2. **Analysis**: Thresholds checked, anomalies detected, forecasts computed
3. **Correlation**: Alerts grouped into incident clusters
4. **Decision**: Gatekeeper approves/denies actions based on SLO state
5. **Execution**: Supervised or dry-run by default
6. **Documentation**: Auto-generated docs, diagrams, reports
7. **Export**: Sanitized artifacts pushed to GitHub portfolio

## Safety Model

- **Supervised mode**: Default. Operator confirms before destructive actions.
- **Break-glass**: Time-limited token for emergency autonomous operations.
- **Gatekeeper**: Blocks actions when SLO is burning or regression detected.
- **Dry-run**: Every subsystem supports preview without execution.
- **Secret scanning**: Pre-commit checks for leaked credentials.
"""

    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    (RELEASE_DIR / "SYSTEM_ARCHITECTURE.md").write_text(content)
    return {"file": "release/v1.0/SYSTEM_ARCHITECTURE.md"}


def build_all():
    results = []
    results.append(generate_release_notes())
    results.append(generate_restore_guide())
    results.append(generate_system_architecture())
    return {"files": [r["file"] for r in results], "count": len(results)}


def main():
    parser = argparse.ArgumentParser(description="Release Build Docs")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = build_all()

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"📝 Generated {result['count']} release docs:")
        for f in result["files"]:
            print(f"  • {f}")

    sys.exit(0)


if __name__ == "__main__":
    main()
