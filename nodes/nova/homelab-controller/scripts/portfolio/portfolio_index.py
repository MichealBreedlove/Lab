#!/usr/bin/env python3
"""portfolio_index.py — Generate recruiter-friendly README index sections."""

import json
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent.parent
LAB_ROOT = ROOT_DIR.parent.parent.parent  # Lab/


def generate_readme_sections() -> str:
    """Generate the portfolio sections for the main README."""
    lines = [
        "## 🏗️ What This Lab Does",
        "",
        "- **Local AI inference cluster** — 4 nodes running Ollama with Qwen 2.5 32B, DeepSeek Coder, LLaMA 3.1 70B",
        "- **AI agent orchestration** — OpenClaw manages autonomous agents across all nodes",
        "- **Infrastructure-as-code** — Ansible playbooks for config management and health checks",
        "- **Self-healing automation** — SLO-driven actions, chaos testing, gatekeeper safety gates",
        "- **Full SRE pipeline** — Snapshots → Evidence → Planning → Actions → SLOs → Incidents → Postmortems",
        "",
        "## 📊 What It Demonstrates",
        "",
        "- **Site Reliability Engineering** — SLOs, error budgets, burn rates, incident management",
        "- **Infrastructure Automation** — Ansible, systemd, scheduled tasks, CI/CD",
        "- **Security Practices** — Secret scanning, sanitization, credential policies, safety gates",
        "- **AI/ML Operations** — Local LLM serving, model management, multi-node inference",
        "- **Documentation Discipline** — Architecture docs, runbooks, postmortems, change logs",
        "",
        "## 🗺️ Architecture",
        "",
        "```",
        "┌──────────────────────────────────────────────────┐",
        "│                    HOMELAB                        │",
        "│                                                  │",
        "│  ┌─────────┐  ┌─────────┐  ┌────────┐  ┌──────┐│",
        "│  │ Jasper   │  │  Nova   │  │  Mira  │  │ Orin ││",
        "│  │ Win11    │  │ Ubuntu  │  │ Ubuntu │  │Ubuntu││",
        "│  │ Gateway  │  │Controller│ │Compute │  │Compute│",
        "│  │ i9-13900K│  │         │  │        │  │      ││",
        "│  │ RTX 4090 │  │ Ansible │  │ Ollama │  │Ollama││",
        "│  │ 64GB     │  │ Ollama  │  │OpenClaw│  │OpenClaw│",
        "│  │ OpenClaw │  │ OpenClaw│  │        │  │      ││",
        "│  └────┬─────┘  └────┬────┘  └───┬────┘  └──┬───┘│",
        "│       └──────┬──────┴──────┬────┘           │    │",
        "│              │   10.1.1.x  │                │    │",
        "│              └─────────────┴────────────────┘    │",
        "└──────────────────────────────────────────────────┘",
        "```",
        "",
        "## 🔧 Priorities Built (P19–P28+)",
        "",
        "| Priority | Feature | Status |",
        "|----------|---------|--------|",
        "| P19 | Chaos Injection Framework | ✅ |",
        "| P20 | Resilience Score + Regression Gate | ✅ |",
        "| P21 | Planner (Goal Engine + What-If) | ✅ |",
        "| P22 | Topology + Service Graph | ✅ |",
        "| P23 | Action Executor + Approval Tiers | ✅ |",
        "| P24 | Evidence Pack + Snapshot Diff | ✅ |",
        "| P25 | Gatekeeper (Safety Gates) | ✅ |",
        "| P26 | Change Management + Release Notes | ✅ |",
        "| P27 | SLOs + Error Budget | ✅ |",
        "| P28 | Incident Commander + Postmortems | ✅ |",
        "| P29 | Portfolio Publisher | ✅ |",
        "",
        "## 📁 Repository Structure",
        "",
        "See [docs/overview.md](docs/overview.md) for full architecture documentation.",
        "",
    ]

    return "\n".join(lines)


def update_readme():
    """Update the Lab README with portfolio sections."""
    readme_path = LAB_ROOT / "README.md"
    existing = readme_path.read_text() if readme_path.exists() else ""

    # Replace content between markers, or append
    marker_start = "<!-- PORTFOLIO_START -->"
    marker_end = "<!-- PORTFOLIO_END -->"

    portfolio_content = f"{marker_start}\n{generate_readme_sections()}\n{marker_end}"

    if marker_start in existing:
        import re
        pattern = re.escape(marker_start) + r'.*?' + re.escape(marker_end)
        updated = re.sub(pattern, portfolio_content, existing, flags=re.DOTALL)
    else:
        # Find a good place to insert (after the first heading)
        lines = existing.split("\n")
        insert_idx = 2  # After title + blank line
        for i, line in enumerate(lines):
            if line.startswith("# "):
                insert_idx = i + 2
                break
        lines.insert(insert_idx, portfolio_content)
        updated = "\n".join(lines)

    readme_path.write_text(updated)
    print(f"README updated at {readme_path}")


if __name__ == "__main__":
    print(generate_readme_sections())
