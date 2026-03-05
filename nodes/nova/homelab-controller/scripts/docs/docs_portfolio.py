#!/usr/bin/env python3
"""P33 supplement — Portfolio Architecture Doc: generate recruiter-grade PORTFOLIO_ARCHITECTURE.md."""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT / "docs" / "generated"


def generate_portfolio():
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    content = """# OpenClaw Autonomous AI Homelab Control Plane

## Overview

A 4-node autonomous infrastructure platform that manages itself: monitoring health, testing resilience, recovering from failures, forecasting capacity, and generating its own documentation — with AI-powered analysis.

Built as a portfolio project demonstrating enterprise-grade SRE, platform engineering, and AI operations practices at homelab scale.

## What It Does

- **Monitors** cluster health via SLO tracking with error budget burn rates
- **Tests** resilience through automated chaos experiments
- **Recovers** from failures with one-command disaster recovery and supervised restore
- **Forecasts** resource exhaustion using linear regression on time-series metrics
- **Detects** anomalies via statistical z-score analysis across all nodes
- **Correlates** alerts into incident clusters across subsystems
- **Analyzes** cluster state using local LLM inference (Ollama + Llama 3)
- **Documents** itself by auto-generating topology, services, dependencies, and changelog
- **Bootstraps** new nodes with zero-touch provisioning
- **Reports** weekly operations summaries with executive-level formatting

## Why It Exists

To prove that one person can design, build, and operate an autonomous infrastructure platform — the same class of system that platform engineering teams at scale companies maintain. Every component is real, tested, and documented.

## Architecture

### Nodes

| Node | Role | Hardware | OS |
|------|------|----------|-----|
| **Jasper** | AI Gateway + GPU Inference | i9-13900K, RTX 4090, 64GB DDR5 | Windows 11 Pro |
| **Nova** | Controller + Orchestrator | Intel N305, 32GB DDR5 | Proxmox/Linux |
| **Mira** | Worker + Compute | i7-2600K, 16GB DDR3 | Proxmox/Linux |
| **Orin** | Worker + Compute | Dell R630, Dual Xeon E5-2667v4, 16GB ECC | Proxmox/Linux |

### Subsystems (P1–P35)

| Layer | Components |
|-------|------------|
| **Core** | SLO monitoring, snapshot pipeline, planner, gatekeeper |
| **Reliability** | Chaos testing, incident memory, disaster recovery |
| **Operations** | Capacity management, node bootstrap, self-documenting architecture |
| **Intelligence** | AIOps anomaly detection, incident correlation, LLM analysis |
| **Infrastructure** | Proxmox cluster, OPNsense firewall, TrueNAS storage, UniFi networking |

### Automation Pipeline

```
oc <command>
  → Gatekeeper (SLO burn check + regression gate)
    → Planner (task scheduling)
      → Controller (Nova orchestrates)
        → Workers (Mira/Orin execute)
          → Artifacts (JSON + dashboard)
            → GitHub (portfolio export)
```

## Key Engineering Decisions

- **Supervised mode by default**: destructive operations require explicit break-glass tokens
- **Dry-run first**: every subsystem supports non-destructive preview before execution
- **Git as source of truth**: all configs, artifacts, and docs committed and versioned
- **Local LLM inference**: Ollama on RTX 4090 for privacy-preserving AI analysis
- **Portfolio-safe exports**: automatic secret redaction before any external push

## Technology Stack

- **Orchestration**: Python 3, Bash, PowerShell
- **Monitoring**: Custom SLO engine, Prometheus-compatible metrics
- **Networking**: OPNsense, UniFi, Tailscale overlay
- **Virtualization**: Proxmox VE cluster
- **Storage**: TrueNAS SCALE, ZFS
- **AI**: Ollama, Llama 3.1, RTX 4090 inference
- **CI/CD**: GitHub Actions, automated secret scanning
- **Documentation**: Auto-generated Mermaid diagrams, Markdown docs

## Diagrams

See `diagrams/` for Mermaid source files:
- `cluster_architecture.mmd` — Full system architecture
- `network_topology.mmd` — Network layout with IP addressing
- `service_dependency_graph.mmd` — Subsystem dependency map
- `compute_pipeline.mmd` — Task execution sequence

## Repository

Source: [MichealBreedlove/Lab](https://github.com/MichealBreedlove/Lab)
"""

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "PORTFOLIO_ARCHITECTURE.md").write_text(content)

    return {"file": "docs/generated/PORTFOLIO_ARCHITECTURE.md", "timestamp": timestamp}


def main():
    parser = argparse.ArgumentParser(description="Generate Portfolio Architecture Doc")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = generate_portfolio()

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"📄 Generated: {result['file']}")

    sys.exit(0)


if __name__ == "__main__":
    main()
