#!/usr/bin/env python3
"""P33 — Services Docs: auto-generate services catalog from configs and scan results."""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
DOCS_DIR = ROOT / "docs" / "generated"


def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def ssh_cmd(host, user, key_path, command, timeout=15):
    key_path = str(Path(key_path).expanduser())
    try:
        r = subprocess.run(
            ["ssh", "-o", "StrictHostKeyChecking=accept-new",
             "-o", "ConnectTimeout=10",
             "-i", key_path,
             f"{user}@{host}", command],
            capture_output=True, text=True, timeout=timeout
        )
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def generate_services():
    profiles = load_json(CONFIG_DIR / "node_profiles.json") or {}
    bootstrap = load_json(CONFIG_DIR / "bootstrap_policy.json") or {}
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    user = bootstrap.get("ssh_user", "micheal")
    key = bootstrap.get("ssh_key_path", "~/.ssh/id_ed25519")

    lines = [
        "# Services Catalog",
        "",
        f"*Auto-generated: {timestamp}*",
        "",
        "## Expected Services by Profile",
        "",
    ]

    for profile_name, profile in profiles.get("profiles", {}).items():
        lines.append(f"### {profile_name}")
        lines.append("")
        lines.append("| Service | Type |")
        lines.append("|---------|------|")
        for svc in profile.get("services", []):
            svc_type = "timer" if ".timer" in svc else "service"
            lines.append(f"| {svc} | {svc_type} |")
        lines.append("")

    lines.extend([
        "## Homelab Controller Subsystems",
        "",
        "| Subsystem | CLI | Config | Scripts |",
        "|-----------|-----|--------|---------|",
        "| DR / Restore | `oc dr *` | `config/dr_policy.json` | `scripts/dr/` |",
        "| Bootstrap | `oc bootstrap *` | `config/bootstrap_policy.json` | `scripts/bootstrap/` |",
        "| Capacity | `oc capacity *` | `config/capacity_policy.json` | `scripts/capacity/` |",
        "| Docs | `oc docs *` | `config/docs_policy.json` | `scripts/docs/` |",
        "| SLO | `oc slo *` | `config/slo_*.json` | `scripts/slo/` |",
        "| Incidents | `oc incident *` | N/A | `scripts/incident/` |",
        "| Dashboard | HTTP | N/A | `dashboard/` |",
        "",
        "## Port Allocations",
        "",
        "| Port | Service | Node(s) |",
        "|------|---------|---------|",
        "| 18789 | OpenClaw Gateway | jasper |",
        "| 18789 | OpenClaw Node | nova, mira, orin |",
        "| 22 | SSH | nova, mira, orin |",
        "| 11434 | Ollama | jasper |",
        "| 8080 | Dashboard | nova |",
        "",
    ])

    # Scan live services (best effort)
    lines.extend(["## Live Service Status", ""])
    for node_name, node_cfg in profiles.get("nodes", {}).items():
        if node_cfg.get("platform") != "linux":
            lines.append(f"### {node_name} (Windows — manual check)")
            lines.append("")
            continue

        lines.append(f"### {node_name} ({node_cfg['ip']})")
        lines.append("")
        result = ssh_cmd(node_cfg["ip"], user, key, "systemctl --user list-units --type=service --state=running --no-pager --no-legend 2>/dev/null | head -10")
        if result:
            lines.append("```")
            lines.append(result)
            lines.append("```")
        else:
            lines.append("*Unable to scan (SSH not available or no user services)*")
        lines.append("")

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "SERVICES.md").write_text("\n".join(lines))

    return {"file": "docs/generated/SERVICES.md"}


def main():
    parser = argparse.ArgumentParser(description="Generate Services Docs")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = generate_services()

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"📄 Generated: {result['file']}")

    sys.exit(0)


if __name__ == "__main__":
    main()
