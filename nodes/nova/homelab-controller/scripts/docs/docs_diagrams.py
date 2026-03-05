#!/usr/bin/env python3
"""P33 supplement — Architecture Diagram Generator: Mermaid diagrams for cluster topology, services, and pipeline."""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
DIAGRAMS_DIR = ROOT / "docs" / "generated" / "diagrams"


def load_json(path):
    with open(path) as f:
        return json.load(f)


def generate_cluster_architecture():
    """Generate Mermaid diagram of cluster architecture."""
    return """graph TB
    subgraph "User Layer"
        USER[👤 Operator / Micheal]
        CLI[OpenClaw CLI]
        DASH[Web Dashboard]
    end

    subgraph "AI Gateway — Jasper"
        direction TB
        GW[OpenClaw Gateway<br/>10.1.1.150]
        GPU[RTX 4090 GPU]
        OLLAMA[Ollama LLM<br/>Inference Engine]
        GW --> GPU
        GW --> OLLAMA
    end

    subgraph "Control Plane — Nova"
        direction TB
        ORCH[Cluster Orchestrator]
        PLAN[Planner]
        GATE[Gatekeeper]
        SLO[SLO Monitor]
        DR[Disaster Recovery]
        CAP[Capacity Manager]
        CHAOS[Chaos Testing]
        AIOPS[AI Operations]
        INC[Incident Memory]
        DOCS[Self-Documenting Arch]
    end

    subgraph "Worker — Mira"
        MIRA_EXEC[Job Execution]
        MIRA_SEC[Security Scans]
        MIRA_TEL[Telemetry]
    end

    subgraph "Compute — Orin"
        ORIN_PROC[Data Processing]
        ORIN_BAK[Backup Tasks]
        ORIN_LOG[Logging]
    end

    subgraph "Infrastructure"
        PROX[Proxmox Cluster]
        OPN[OPNsense Firewall]
        SWITCH[Managed Switches]
        NAS[TrueNAS Storage]
    end

    subgraph "External"
        GH[GitHub<br/>MichealBreedlove/Lab]
    end

    USER --> CLI
    USER --> DASH
    CLI --> GW
    DASH --> GW
    GW <-->|SSH + API| ORCH
    ORCH --> PLAN
    ORCH --> GATE
    ORCH --> SLO
    ORCH --> DR
    ORCH --> CAP
    ORCH --> CHAOS
    ORCH --> AIOPS
    ORCH --> INC
    ORCH --> DOCS
    ORCH <-->|Task Dispatch| MIRA_EXEC
    ORCH <-->|Compute Jobs| ORIN_PROC
    ORCH -->|Management| PROX
    ORCH -->|Backup + Portfolio| GH
    PROX --> OPN
    PROX --> SWITCH
    PROX --> NAS

    classDef gateway fill:#f97316,stroke:#ea580c,color:#fff
    classDef control fill:#2563eb,stroke:#1d4ed8,color:#fff
    classDef compute fill:#16a34a,stroke:#15803d,color:#fff
    classDef infra fill:#6b7280,stroke:#4b5563,color:#fff
    classDef external fill:#8b5cf6,stroke:#7c3aed,color:#fff

    class GW,GPU,OLLAMA gateway
    class ORCH,PLAN,GATE,SLO,DR,CAP,CHAOS,AIOPS,INC,DOCS control
    class MIRA_EXEC,MIRA_SEC,MIRA_TEL,ORIN_PROC,ORIN_BAK,ORIN_LOG compute
    class PROX,OPN,SWITCH,NAS infra
    class GH external
"""


def generate_network_topology():
    """Generate Mermaid diagram of network topology."""
    profiles = load_json(CONFIG_DIR / "node_profiles.json")

    diagram = """graph LR
    subgraph "10.1.1.0/24 — Homelab Network"
        direction TB

        GW["🔥 OPNsense<br/>10.1.1.1<br/>Gateway/Firewall"]
        AP["📡 UniFi U7 Pro XG<br/>10.1.1.19<br/>WiFi AP"]

        subgraph "AI Cluster"
"""
    for name, cfg in profiles.get("nodes", {}).items():
        icon = "🖥️" if cfg.get("platform") == "windows" else "🐧"
        profile = profiles["profiles"].get(cfg.get("profile", ""), {})
        roles = ", ".join(profile.get("roles", []))
        diagram += f'            {name.upper()}["{icon} {name}<br/>{cfg["ip"]}<br/>{roles}"]\n'

    diagram += """        end

        subgraph "Infrastructure"
            NAS["💾 TrueNAS<br/>10.1.1.11"]
            PROX1["🖥️ Proxmox-1<br/>10.1.1.2"]
            PROX2["🖥️ Proxmox-2<br/>10.1.1.4"]
            PROX3["🖥️ Proxmox-3<br/>10.1.1.5"]
        end

        GW --- AP
        GW --- JASPER
        GW --- NOVA
        GW --- MIRA
        GW --- ORIN
        GW --- NAS
        PROX1 --- NOVA
        PROX2 --- MIRA
        PROX3 --- ORIN
    end

    INTERNET["🌐 Internet"] --> GW

    classDef firewall fill:#ef4444,stroke:#dc2626,color:#fff
    classDef node fill:#2563eb,stroke:#1d4ed8,color:#fff
    classDef infra fill:#6b7280,stroke:#4b5563,color:#fff
    classDef external fill:#8b5cf6,stroke:#7c3aed,color:#fff

    class GW firewall
    class JASPER,NOVA,MIRA,ORIN node
    class NAS,PROX1,PROX2,PROX3,AP infra
    class INTERNET external
"""
    return diagram


def generate_service_dependency():
    """Generate Mermaid diagram of service dependencies."""
    return """graph TD
    subgraph "CLI Layer"
        OC[oc.sh CLI]
    end

    subgraph "Core Services"
        SLO[SLO Monitor]
        SNAP[Snapshot Pipeline]
        PLAN[Planner]
        GATE[Gatekeeper]
    end

    subgraph "Operations"
        DR[Disaster Recovery]
        BOOT[Bootstrap]
        CAP[Capacity Manager]
        CHAOS[Chaos Engine]
    end

    subgraph "Intelligence"
        AIOPS[AIOps Layer]
        DOCS[Self-Documenting Arch]
        INC[Incident Memory]
    end

    subgraph "Presentation"
        DASH[Dashboard]
        REPORT[Operations Reports]
    end

    subgraph "Data"
        ARTIFACTS[(artifacts/)]
        CONFIG[(config/)]
    end

    OC --> SLO
    OC --> DR
    OC --> BOOT
    OC --> CAP
    OC --> CHAOS
    OC --> AIOPS
    OC --> DOCS

    SLO --> ARTIFACTS
    SNAP --> ARTIFACTS
    PLAN --> GATE
    PLAN --> SLO

    DR --> SNAP
    DR --> CONFIG
    BOOT --> CONFIG
    CAP --> ARTIFACTS
    CHAOS --> GATE
    CHAOS --> SLO

    AIOPS --> ARTIFACTS
    AIOPS --> INC
    DOCS --> CONFIG
    DOCS --> ARTIFACTS

    DASH --> ARTIFACTS
    REPORT --> AIOPS

    classDef cli fill:#f59e0b,stroke:#d97706,color:#000
    classDef core fill:#2563eb,stroke:#1d4ed8,color:#fff
    classDef ops fill:#16a34a,stroke:#15803d,color:#fff
    classDef intel fill:#8b5cf6,stroke:#7c3aed,color:#fff
    classDef present fill:#ec4899,stroke:#db2777,color:#fff
    classDef data fill:#6b7280,stroke:#4b5563,color:#fff

    class OC cli
    class SLO,SNAP,PLAN,GATE core
    class DR,BOOT,CAP,CHAOS ops
    class AIOPS,DOCS,INC intel
    class DASH,REPORT present
    class ARTIFACTS,CONFIG data
"""


def generate_compute_pipeline():
    """Generate Mermaid diagram of compute/automation pipeline."""
    return """sequenceDiagram
    participant User as 👤 Operator
    participant CLI as oc CLI
    participant Gate as Gatekeeper
    participant Plan as Planner
    participant Nova as Nova (Controller)
    participant Workers as Mira/Orin (Workers)
    participant Jasper as Jasper (GPU)
    participant GH as GitHub

    User->>CLI: oc <command>
    CLI->>Gate: Request approval
    Gate->>Gate: Check SLO burn rate
    Gate->>Gate: Check regression gate
    Gate-->>CLI: ALLOW / DENY

    alt Approved
        CLI->>Plan: Submit task
        Plan->>Nova: Schedule on controller
        Nova->>Workers: Dispatch subtasks
        Workers-->>Nova: Results
        Nova->>Jasper: AI analysis (if needed)
        Jasper-->>Nova: LLM response
        Nova->>Nova: Update artifacts
        Nova->>GH: Push to portfolio
        Nova-->>CLI: Complete
        CLI-->>User: ✅ Done
    else Denied
        Gate-->>User: ❌ Blocked (reason)
    end
"""


def generate_all_diagrams():
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    DIAGRAMS_DIR.mkdir(parents=True, exist_ok=True)

    diagrams = {
        "cluster_architecture": generate_cluster_architecture(),
        "network_topology": generate_network_topology(),
        "service_dependency_graph": generate_service_dependency(),
        "compute_pipeline": generate_compute_pipeline(),
    }

    generated = []
    for name, content in diagrams.items():
        # Write as .mmd (Mermaid source)
        mmd_path = DIAGRAMS_DIR / f"{name}.mmd"
        mmd_path.write_text(content)
        generated.append(str(mmd_path.relative_to(ROOT)))

        # Write as embeddable markdown
        md_path = DIAGRAMS_DIR / f"{name}.md"
        md_path.write_text(f"# {name.replace('_', ' ').title()}\n\n```mermaid\n{content}\n```\n")
        generated.append(str(md_path.relative_to(ROOT)))

    return {"timestamp": timestamp, "diagrams": generated, "count": len(diagrams)}


def main():
    parser = argparse.ArgumentParser(description="Generate Architecture Diagrams")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = generate_all_diagrams()

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"🎨 Generated {result['count']} diagrams ({len(result['diagrams'])} files)")
        for f in result["diagrams"]:
            print(f"  • {f}")

    sys.exit(0)


if __name__ == "__main__":
    main()
