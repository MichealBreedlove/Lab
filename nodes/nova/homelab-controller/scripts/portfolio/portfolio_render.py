#!/usr/bin/env python3
"""P39 — Portfolio Renderer: generate recruiter-grade markdown docs from all subsystem artifacts."""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts"
CONFIG = ROOT / "config"
META_DIR = ROOT.parents[2] / "_meta"  # Lab/_meta/


def load_json_safe(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def render_readme():
    return """# OpenClaw Autonomous AI Homelab Control Plane

**Author:** Micheal Breedlove

A fully automated AI infrastructure platform that operates and self-heals a distributed 4-node homelab cluster. Demonstrates capabilities found in modern platform engineering and SRE environments.

## Core Capabilities

- **Autonomous cluster orchestration** across 4 heterogeneous nodes
- **SLO monitoring** with error budget burn-rate protection
- **Chaos engineering** experiments with automated remediation
- **Disaster recovery** automation with one-command restore and drill validation
- **AI-driven operations** analysis using local LLM inference
- **Infrastructure-as-code** with automated config backup and export
- **Self-documenting architecture** with auto-generated topology and diagrams
- **Observability stack** (Prometheus, Grafana, Loki, Alertmanager)
- **Security hygiene** with baseline auditing and secret scanning
- **Zero-touch node bootstrap** for cluster expansion

## Architecture

| Node | Role | Hardware |
|------|------|----------|
| **Jasper** | AI Gateway + GPU Inference | i9-13900K, RTX 4090, 64GB DDR5 |
| **Nova** | Controller + Orchestrator | Intel N305, 32GB DDR5 |
| **Mira** | Worker + Compute | i7-2600K, 16GB DDR3 |
| **Orin** | Worker + Compute | Dell R630, Dual Xeon E5-2667v4, 16GB ECC |

## Automation Layers

| Layer | Subsystems |
|-------|-----------|
| Core | SLO monitoring, snapshot pipeline, planner, gatekeeper |
| Reliability | Chaos testing, incident memory, disaster recovery |
| Operations | Capacity management, node bootstrap, infrastructure backup |
| Intelligence | AIOps anomaly detection, incident correlation, LLM analysis |
| Observability | Prometheus, Grafana, Loki, Alertmanager, event bus |
| Security | Baseline auditing, secret scanning, redaction library |
| Documentation | Auto-generated topology, services, dependencies, diagrams |

## Operational Safety

- **Supervised mode** by default — destructive operations require break-glass tokens
- **Dry-run first** — every subsystem supports preview before execution
- **Gatekeeper** blocks actions when SLO is burning
- **Secret scanning** enforced before every git push

## Documentation

- [Architecture Overview](_meta/ARCHITECTURE.md)
- [System Capabilities](_meta/CAPABILITIES.md)
- [Operations Summary](_meta/OPERATIONS.md)
- [Security Model](_meta/SECURITY.md)
- [Observability Stack](_meta/OBSERVABILITY.md)
- [Infrastructure Inventory](_meta/INFRA.md)
"""


def render_capabilities():
    return """# System Capabilities

## Platform Engineering

### Infrastructure Automation
- Cluster orchestration across 4 nodes (3 Linux + 1 Windows)
- Automated remediation workflows via gatekeeper-approved actions
- Autonomous capacity planning with forecasting

### Reliability Engineering
- SLO monitoring with error budget burn-rate protection
- Chaos engineering experiments with automated detection/recovery
- Incident detection, correlation, and remediation memory

### Disaster Recovery
- Automated DR validation drills with MTTR tracking
- One-command restore orchestration across nodes
- Snapshot-based system recovery with freshness tracking

### AI Operations
- AI-generated cluster analysis via local LLM (Ollama + Llama 3)
- Statistical anomaly detection (z-score) on capacity metrics
- Cross-subsystem incident correlation
- Weekly operations reports with executive summaries

### Observability
- Prometheus metrics collection with alerting rules
- Grafana dashboards for visualization
- Loki log aggregation with Promtail shipping
- Internal event bus for subsystem coordination

### Security
- SSH baseline auditing across all nodes
- Automated secret scanning before every git push
- Shared redaction library for consistent secret removal
- Firewall and port monitoring

### Infrastructure Management
- Proxmox cluster config export and backup
- OPNsense firewall backup workflow
- Network switch documentation
- Node inventory collection (hardware, OS, services, ports)

## Technology Stack

Python 3, Bash, PowerShell, Docker Compose, Prometheus, Grafana, Loki, Alertmanager,
Proxmox VE, OPNsense, TrueNAS, UniFi, Ollama, Git, GitHub Actions
"""


def render_operations():
    dr = load_json_safe(ARTIFACTS / "dr" / "dr_status.json")
    cap = load_json_safe(ARTIFACTS / "capacity" / "latest.json")

    lines = ["# Operations Summary\n"]

    if dr:
        lines.append(f"## Disaster Recovery\n- Status: {dr.get('status', '?')} (score: {dr.get('readiness_score', '?')})")
        if dr.get('last_drill_mttr_sec'):
            lines.append(f"- Last drill MTTR: {dr['last_drill_mttr_sec']}s")
    else:
        lines.append("## Disaster Recovery\n- No DR data available\n")

    if cap:
        lines.append(f"\n## Capacity ({cap.get('timestamp', '')[:19]})")
        for name, data in cap.get("nodes", {}).items():
            if data.get("status") == "ok":
                lines.append(f"- {name}: CPU {data.get('cpu_pct','?')}% | Mem {data.get('memory_pct','?')}% | Disk {data.get('disk_pct','?')}%")
    else:
        lines.append("\n## Capacity\n- No capacity data available\n")

    return "\n".join(lines)


def render_security():
    sec = load_json_safe(ARTIFACTS / "security" / "sec_audit_latest.json")
    scan = load_json_safe(ARTIFACTS / "security" / "secretscan_latest.json")

    lines = ["# Security Summary\n"]
    if sec:
        for name, data in sec.get("nodes", {}).items():
            s = data.get("summary", {})
            if s:
                lines.append(f"- {name}: {s.get('score', 0)}% ({s.get('passing', 0)}/{s.get('total', 0)} checks)")
    if scan:
        lines.append(f"\n## Secret Scan\n- Files scanned: {scan.get('files_scanned', 0)}")
        lines.append(f"- Violations: {scan.get('violation_count', 0)}")
        lines.append(f"- Status: {'✅ Clean' if scan.get('pass') else '❌ Violations found'}")

    return "\n".join(lines)


def render_all(lab_path):
    lab = Path(lab_path) if lab_path else ROOT.parents[2]
    meta = lab / "_meta"
    meta.mkdir(parents=True, exist_ok=True)

    docs = {
        "PORTFOLIO_README.md": render_readme(),
        "CAPABILITIES.md": render_capabilities(),
        "OPERATIONS.md": render_operations(),
        "SECURITY.md": render_security(),
    }

    for filename, content in docs.items():
        (meta / filename).write_text(content)

    return {"files": list(docs.keys()), "output_dir": str(meta)}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--lab-repo", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = render_all(args.lab_repo)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"📦 Portfolio rendered: {len(result['files'])} docs → {result['output_dir']}")
        for f in result["files"]:
            print(f"  • {f}")
