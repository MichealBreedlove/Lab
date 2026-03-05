#!/usr/bin/env python3
"""P33 — Topology Docs: auto-generate network topology documentation from configs."""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
DOCS_DIR = ROOT / "docs" / "generated"


def load_json(path):
    with open(path) as f:
        return json.load(f)


def generate_topology():
    profiles = load_json(CONFIG_DIR / "node_profiles.json")
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    lines = [
        "# Network Topology",
        "",
        f"*Auto-generated: {timestamp}*",
        "",
        "## Cluster Nodes",
        "",
        "| Node | IP | Platform | Profile | Roles |",
        "|------|-----|----------|---------|-------|",
    ]

    for name, cfg in profiles.get("nodes", {}).items():
        profile = profiles["profiles"].get(cfg.get("profile", ""), {})
        roles = ", ".join(profile.get("roles", []))
        lines.append(f"| {name} | {cfg['ip']} | {cfg.get('platform', '?')} | {cfg.get('profile', '?')} | {roles} |")

    lines.extend(["", "## Node Profiles", ""])

    for name, profile in profiles.get("profiles", {}).items():
        lines.append(f"### {name}")
        lines.append(f"")
        lines.append(f"- **Description:** {profile.get('description', 'N/A')}")
        lines.append(f"- **OpenClaw Mode:** {profile.get('openclaw_mode', 'N/A')}")
        lines.append(f"- **Packages:** {', '.join(profile.get('packages', []))}")
        lines.append(f"- **Services:** {', '.join(profile.get('services', []))}")
        lines.append(f"- **Roles:** {', '.join(profile.get('roles', []))}")
        lines.append("")

    lines.extend([
        "## Network Layout",
        "",
        "```",
        "┌─────────────────────────────────────────────┐",
        "│              OPNsense Gateway                │",
        "│              10.1.1.1                        │",
        "└────────────────────┬────────────────────────┘",
        "                     │",
        "        ┌────────────┼────────────┐",
        "        │            │            │",
    ])

    nodes = list(profiles.get("nodes", {}).items())
    for i, (name, cfg) in enumerate(nodes):
        ip = cfg["ip"]
        lines.append(f"   ┌────────────┐")
        lines.append(f"   │ {name:<10} │")
        lines.append(f"   │ {ip:<10} │")
        lines.append(f"   └────────────┘")
        if i < len(nodes) - 1:
            lines.append(f"        │")

    lines.append("```")
    lines.append("")

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    output = "\n".join(lines)
    (DOCS_DIR / "TOPOLOGY.md").write_text(output)

    return {"file": "docs/generated/TOPOLOGY.md", "nodes": len(profiles.get("nodes", {})), "profiles": len(profiles.get("profiles", {}))}


def main():
    parser = argparse.ArgumentParser(description="Generate Topology Docs")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = generate_topology()

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"📄 Generated: {result['file']} ({result['nodes']} nodes, {result['profiles']} profiles)")

    sys.exit(0)


if __name__ == "__main__":
    main()
