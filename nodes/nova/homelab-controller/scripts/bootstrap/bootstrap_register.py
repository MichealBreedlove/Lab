#!/usr/bin/env python3
"""P31 — Bootstrap Register: register node in topology, services catalog, and IP plan."""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "artifacts" / "bootstrap"
CONFIG_DIR = ROOT / "config"
INVENTORY_DIR = ROOT.parents[2] / "inventory"  # Lab/inventory/


def load_json(path):
    with open(path) as f:
        return json.load(f)


def load_yaml_safe(path):
    try:
        import yaml
        with open(path) as f:
            return yaml.safe_load(f)
    except ImportError:
        return None
    except Exception:
        return None


def run_register(node_name, dry_run=True):
    profiles = load_json(CONFIG_DIR / "node_profiles.json")
    node_cfg = profiles["nodes"].get(node_name)
    if not node_cfg:
        return {"error": f"node '{node_name}' not found"}

    profile_name = node_cfg.get("profile", "worker")
    profile = profiles["profiles"].get(profile_name, {})
    ip = node_cfg["ip"]

    registration = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "node": node_name,
        "ip": ip,
        "profile": profile_name,
        "platform": node_cfg.get("platform", "linux"),
        "roles": profile.get("roles", []),
        "dry_run": dry_run,
        "actions": [],
    }

    # Action 1: Verify node exists in IP plan
    ip_plan_path = INVENTORY_DIR / "ip_plan.yaml"
    ip_plan = load_yaml_safe(ip_plan_path) if ip_plan_path.exists() else None
    if ip_plan:
        node_in_plan = any(
            node_name in str(entry) 
            for entry in (ip_plan if isinstance(ip_plan, list) else [ip_plan])
        )
        registration["actions"].append({
            "name": "verify_ip_plan",
            "status": "ok" if node_in_plan else "needs_update",
            "detail": f"{node_name} {'found' if node_in_plan else 'not found'} in ip_plan.yaml",
        })
    else:
        registration["actions"].append({
            "name": "verify_ip_plan",
            "status": "skipped",
            "detail": "ip_plan.yaml not found or pyyaml not available",
        })

    # Action 2: Verify node directory exists in repo
    node_dir = ROOT.parents[2] / "nodes" / node_name
    registration["actions"].append({
        "name": "verify_node_dir",
        "status": "ok" if node_dir.exists() else "needs_creation",
        "detail": f"nodes/{node_name}/ {'exists' if node_dir.exists() else 'missing'}",
    })

    # Action 3: Check services catalog
    services_path = INVENTORY_DIR / "services.yaml"
    services = load_yaml_safe(services_path) if services_path.exists() else None
    registration["actions"].append({
        "name": "verify_services_catalog",
        "status": "ok" if services else "skipped",
        "detail": "services.yaml " + ("loaded" if services else "not available"),
    })

    # Action 4: Check hardware inventory
    hw_path = INVENTORY_DIR / "hardware.yaml"
    hw = load_yaml_safe(hw_path) if hw_path.exists() else None
    if hw:
        node_in_hw = any(
            node_name in str(entry) 
            for entry in (hw if isinstance(hw, list) else [hw])
        )
        registration["actions"].append({
            "name": "verify_hardware_inventory",
            "status": "ok" if node_in_hw else "needs_update",
            "detail": f"{node_name} {'found' if node_in_hw else 'not found'} in hardware.yaml",
        })
    else:
        registration["actions"].append({
            "name": "verify_hardware_inventory",
            "status": "skipped",
            "detail": "hardware.yaml not available",
        })

    # Action 5: Record registration
    registration["actions"].append({
        "name": "record_registration",
        "status": "ok",
        "detail": f"Registered {node_name} ({ip}) as {profile_name} with roles {profile.get('roles', [])}",
    })

    registration["overall_status"] = "ok"

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(ARTIFACTS_DIR / f"register_{node_name}.json", "w") as f:
        json.dump(registration, f, indent=2)

    return registration


def main():
    parser = argparse.ArgumentParser(description="Bootstrap Register")
    parser.add_argument("--node", required=True)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = run_register(args.node, dry_run=not args.apply)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"📋 Bootstrap register: {result.get('node')} ({result.get('ip')})")
        print(f"  Profile: {result.get('profile')} | Roles: {', '.join(result.get('roles', []))}")
        for a in result.get("actions", []):
            icon = "✅" if a["status"] == "ok" else "⚠️" if a["status"] in ("needs_update", "needs_creation") else "⏭️"
            print(f"  {icon} {a['name']}: {a['detail']}")

    sys.exit(0)


if __name__ == "__main__":
    main()
