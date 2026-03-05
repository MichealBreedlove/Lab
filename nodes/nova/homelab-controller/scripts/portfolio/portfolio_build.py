#!/usr/bin/env python3
"""portfolio_build.py — Build the MkDocs site content from Lab repo data."""

import json
import shutil
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent.parent
LAB_ROOT = ROOT_DIR.parent.parent.parent  # Lab/
SITE_DIR = LAB_ROOT / "site" / "docs"
CONFIG_DIR = ROOT_DIR / "config"


def load_policy():
    with open(CONFIG_DIR / "portfolio_policy.json") as f:
        return json.load(f)


def build_node_pages():
    """Generate per-node documentation pages."""
    nodes_dir = SITE_DIR / "nodes"
    nodes_dir.mkdir(parents=True, exist_ok=True)

    nodes = {
        "jasper": {
            "role": "Gateway + Workstation",
            "os": "Windows 11 Pro",
            "specs": "Intel i9-13900K, 64GB RAM, RTX 4090",
            "services": ["OpenClaw Gateway", "Development Environment"],
        },
        "nova": {
            "role": "Ansible Controller + AI Compute",
            "os": "Ubuntu",
            "specs": "See inventory/hardware.yaml",
            "services": ["Ansible", "Ollama", "OpenClaw Node", "Homelab Controller"],
        },
        "mira": {
            "role": "AI Compute Node",
            "os": "Ubuntu",
            "specs": "See inventory/hardware.yaml",
            "services": ["Ollama", "OpenClaw Node"],
        },
        "orin": {
            "role": "AI Compute Node",
            "os": "Ubuntu",
            "specs": "See inventory/hardware.yaml",
            "services": ["Ollama", "OpenClaw Node"],
        },
    }

    for name, info in nodes.items():
        content = f"""# {name.capitalize()}

**Role:** {info['role']}
**OS:** {info['os']}
**Specs:** {info['specs']}

## Services
{"".join(f"- {s}" + chr(10) for s in info['services'])}

## Configuration
See `nodes/{name}/` in the repository for configuration files and state exports.

## Change Log
See `nodes/{name}/logs/change_log.md` for recent changes.
"""
        (nodes_dir / f"{name}.md").write_text(content, encoding="utf-8")

    print(f"  Built {len(nodes)} node pages")


def build_system_pages():
    """Generate system/service documentation pages."""
    systems_dir = SITE_DIR / "systems"
    systems_dir.mkdir(parents=True, exist_ok=True)

    systems = {
        "openclaw": ("OpenClaw", "AI agent orchestration platform managing autonomous agents across all nodes."),
        "proxmox": ("Proxmox", "Virtualization platform for VM and container management."),
        "truenas": ("TrueNAS", "Network-attached storage for shared datasets and backups."),
        "opnsense": ("OPNsense", "Firewall and network security on Qotom Q20342G9."),
        "networking": ("Networking", "UniFi U7 Pro XG AP, 10.1.1.0/24 subnet, Tailscale overlay."),
    }

    for key, (title, desc) in systems.items():
        content = f"""# {title}

{desc}

## Configuration
See `services/{key}/` in the repository for configuration and documentation.

## Related
- [Architecture Overview](../index.md)
"""
        (systems_dir / f"{key}.md").write_text(content, encoding="utf-8")

    print(f"  Built {len(systems)} system pages")


def build_pipeline_pages():
    """Generate pipeline documentation pages."""
    pipelines_dir = SITE_DIR / "pipelines"
    pipelines_dir.mkdir(parents=True, exist_ok=True)

    pipelines = {
        "snapshots": ("Snapshots", "P24", "Periodic infrastructure state capture and diff analysis."),
        "chaos": ("Chaos Testing", "P19-P20", "Controlled failure injection to validate resilience."),
        "planner": ("Planner", "P21", "Goal engine with what-if analysis for infrastructure decisions."),
        "actions": ("Action Executor", "P23", "Tiered action execution with approval gates."),
        "evidence": ("Evidence Packs", "P24", "Automated evidence collection for audit and compliance."),
        "gatekeeper": ("Gatekeeper", "P25", "Safety gates that evaluate conditions before allowing actions."),
        "slo": ("SLOs + Error Budget", "P27", "Service level objectives with burn rate tracking and budget management."),
        "incidents": ("Incident Commander", "P28", "Automated incident lifecycle with timeline and postmortem generation."),
    }

    for key, (title, priority, desc) in pipelines.items():
        content = f"""# {title} ({priority})

{desc}

## How It Works
See the homelab-controller scripts and configuration for implementation details.

## CLI
```bash
oc {key} status    # Check current state
oc {key} test      # Run tests
```

## Related
- [SLO Dashboard](../reports/latest_slo.md)
- [Architecture Overview](../index.md)
"""
        (pipelines_dir / f"{key}.md").write_text(content, encoding="utf-8")

    print(f"  Built {len(pipelines)} pipeline pages")


def build_diagram_files():
    """Generate Mermaid diagram files."""
    diagrams_dir = SITE_DIR / "diagrams"
    diagrams_dir.mkdir(parents=True, exist_ok=True)

    # Topology diagram
    (diagrams_dir / "topology.mmd").write_text("""graph TB
    subgraph "Home Lab Network (10.1.1.0/24)"
        Internet((Internet)) --> OPNsense[OPNsense Firewall]
        OPNsense --> UniFi[UniFi U7 Pro XG]
        UniFi --> Jasper[Jasper - Win11 Gateway<br/>i9-13900K / RTX 4090 / 64GB]
        UniFi --> Nova[Nova - Ubuntu Controller<br/>Ansible + Ollama]
        UniFi --> Mira[Mira - Ubuntu Compute<br/>Ollama + OpenClaw]
        UniFi --> Orin[Orin - Ubuntu Compute<br/>Ollama + OpenClaw]
    end

    Jasper -->|OpenClaw Gateway| Nova
    Jasper -->|OpenClaw Gateway| Mira
    Jasper -->|OpenClaw Gateway| Orin
    Nova -->|Ansible SSH| Mira
    Nova -->|Ansible SSH| Orin
""")

    # Services diagram
    (diagrams_dir / "services.mmd").write_text("""graph LR
    subgraph "AI Stack"
        Ollama[Ollama<br/>LLM Inference]
        OpenClaw[OpenClaw<br/>Agent Orchestration]
        Models[Models<br/>Qwen/DeepSeek/LLaMA]
    end

    subgraph "Infrastructure"
        Ansible[Ansible<br/>Config Management]
        Proxmox[Proxmox<br/>Virtualization]
        TrueNAS[TrueNAS<br/>Storage]
    end

    subgraph "SRE Pipeline"
        Snapshots --> Evidence
        Evidence --> Planner
        Planner --> Actions
        Actions --> Gatekeeper
        SLO --> Incidents
        Incidents --> Postmortem
    end

    OpenClaw --> Ollama
    Ollama --> Models
    Ansible --> Snapshots
""")

    # Dependencies diagram
    (diagrams_dir / "dependencies.mmd").write_text("""graph TD
    P19[P19: Chaos Injection] --> P20[P20: Resilience Score]
    P20 --> P21[P21: Planner]
    P21 --> P23[P23: Action Executor]
    P22[P22: Topology Graph] --> P23
    P23 --> P25[P25: Gatekeeper]
    P24[P24: Evidence Packs] --> P25
    P25 --> P27[P27: SLOs]
    P27 --> P28[P28: Incidents]
    P26[P26: Changelog] --> P29[P29: Portfolio]
    P28 --> P29
""")

    print(f"  Built 3 Mermaid diagrams")


def build_index():
    """Generate the main site index page."""
    content = """# Home Lab — Infrastructure Portfolio

> Multi-node AI inference and SRE automation cluster built by Micheal Breedlove.

## 30-Second Tour

🏗️ **What:** A 4-node homelab running local AI models with full SRE automation.

🔧 **How:** OpenClaw orchestrates AI agents, Ansible manages config, custom Python pipelines handle SLOs, incidents, chaos testing, and evidence packs.

📊 **Why:** Portfolio demonstrating infrastructure automation, site reliability engineering, security practices, and AI/ML operations.

### What I Built
- Local LLM cluster serving Qwen 2.5 32B, DeepSeek Coder v2, LLaMA 3.1 70B
- AI agent orchestration across 4 nodes with OpenClaw
- Full SRE pipeline: Chaos → Resilience → Planning → Actions → SLOs → Incidents
- Automated backups, secret scanning, and recruiter-grade documentation

### What It Demonstrates
- Site Reliability Engineering (SLOs, error budgets, incident management)
- Infrastructure as Code (Ansible, systemd, CI/CD)
- Security (secret scanning, credential policies, safety gates)
- AI/ML Operations (multi-node inference, model management)
- Documentation Discipline (architecture docs, runbooks, postmortems)

## Architecture

```mermaid
graph TB
    subgraph "Home Lab (10.1.1.0/24)"
        Jasper[Jasper<br/>Win11 / i9-13900K / RTX 4090]
        Nova[Nova<br/>Ubuntu / Controller]
        Mira[Mira<br/>Ubuntu / Compute]
        Orin[Orin<br/>Ubuntu / Compute]
    end
    Jasper -->|Gateway| Nova & Mira & Orin
    Nova -->|Ansible| Mira & Orin
```

## Nodes
- [Jasper](nodes/jasper.md) — Windows 11 Gateway
- [Nova](nodes/nova.md) — Ubuntu Controller
- [Mira](nodes/mira.md) — Ubuntu Compute
- [Orin](nodes/orin.md) — Ubuntu Compute

## Systems
- [OpenClaw](systems/openclaw.md) — AI Agent Orchestration
- [Proxmox](systems/proxmox.md) — Virtualization
- [TrueNAS](systems/truenas.md) — Storage
- [OPNsense](systems/opnsense.md) — Firewall
- [Networking](systems/networking.md) — UniFi + Tailscale

## SRE Pipelines
- [Chaos Testing](pipelines/chaos.md)
- [SLOs + Error Budget](pipelines/slo.md)
- [Incident Commander](pipelines/incidents.md)
- [Gatekeeper](pipelines/gatekeeper.md)
- [Evidence Packs](pipelines/evidence.md)

## Reports
- [Latest SLO Report](reports/latest_slo.md)
- [Latest Incident](reports/latest_incident.md)

---
*Auto-generated by the Portfolio Publisher pipeline.*
"""
    (SITE_DIR / "index.md").write_text(content, encoding='utf-8')
    print("  Built index.md")


def build_report_placeholders():
    """Create placeholder report pages."""
    reports_dir = SITE_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    for name in ["latest_snapshot", "latest_plan", "latest_slo",
                  "latest_incident", "latest_evidence"]:
        (reports_dir / f"{name}.md").write_text(
            f"# {name.replace('_', ' ').title()}\n\n"
            f"*Auto-populated when the pipeline runs on Nova.*\n"
        )

    print("  Built 5 report placeholders")


def build_all():
    """Build all site content."""
    print("=== Portfolio Build ===")
    SITE_DIR.mkdir(parents=True, exist_ok=True)

    build_index()
    build_node_pages()
    build_system_pages()
    build_pipeline_pages()
    build_diagram_files()
    build_report_placeholders()

    print("=== Build complete ===")


if __name__ == "__main__":
    build_all()
