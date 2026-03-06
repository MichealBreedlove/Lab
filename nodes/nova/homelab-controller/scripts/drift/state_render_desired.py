#!/usr/bin/env python3
"""Render desired-state files from config/desired_state.json into state/desired/."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG = ROOT / "config" / "desired_state.json"
DESIRED_DIR = ROOT / "state" / "desired"


def render():
    with open(CONFIG) as f:
        config = json.load(f)

    DESIRED_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    # Render per-node desired state
    for name, spec in config.get("nodes", {}).items():
        node_dir = DESIRED_DIR / name
        node_dir.mkdir(exist_ok=True)

        desired = {
            "node": name,
            "timestamp": timestamp,
            "ip": spec.get("ip"),
            "role": spec.get("role"),
            "services": spec.get("services", []),
            "ports": spec.get("ports", []),
            "packages": spec.get("packages", []),
            "ssh_config": spec.get("ssh_config", {}),
            "firewall": spec.get("firewall", {}),
        }

        with open(node_dir / "desired.json", "w") as f:
            json.dump(desired, f, indent=2)

    # Render infrastructure desired state
    infra = config.get("infrastructure", {})
    infra_dir = DESIRED_DIR / "infrastructure"
    infra_dir.mkdir(exist_ok=True)

    with open(infra_dir / "desired.json", "w") as f:
        json.dump({"timestamp": timestamp, **infra}, f, indent=2)

    print(f"[OK] Desired state rendered to {DESIRED_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(render())
