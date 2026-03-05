#!/usr/bin/env python3
"""P37 — Infrastructure Status Publisher: generate infra_status.json for dashboard."""

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "artifacts" / "infra"
DASHBOARD_DATA = ROOT / "dashboard" / "static" / "data"


def load_json_safe(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def publish():
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    inventory = load_json_safe(ARTIFACTS_DIR / "inventory_latest.json")
    proxmox = load_json_safe(ARTIFACTS_DIR / "proxmox" / "export_summary.json")
    opnsense = load_json_safe(ARTIFACTS_DIR / "opnsense" / "backup_status.json")

    nodes_ok = 0
    nodes_total = 0
    if inventory:
        for name, data in inventory.get("nodes", {}).items():
            nodes_total += 1
            if data.get("status") != "skipped" and data.get("hostname"):
                nodes_ok += 1

    proxmox_exported = 0
    if proxmox:
        for host, data in proxmox.get("hosts", {}).items():
            proxmox_exported += sum(1 for f in data.get("files", {}).values() if f.get("exported"))

    opnsense_fresh = opnsense.get("latest_fresh", False) if opnsense else False

    status = "GREEN" if nodes_ok == nodes_total and opnsense_fresh else "YELLOW" if nodes_ok > 0 else "RED"

    result = {
        "timestamp": timestamp,
        "status": status,
        "inventory": {"nodes_ok": nodes_ok, "nodes_total": nodes_total, "last_scan": inventory.get("timestamp") if inventory else None},
        "proxmox": {"files_exported": proxmox_exported, "last_export": proxmox.get("timestamp") if proxmox else None},
        "opnsense": {"has_backup": opnsense.get("has_backup", False) if opnsense else False, "fresh": opnsense_fresh},
    }

    DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)
    with open(DASHBOARD_DATA / "infra_status.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


if __name__ == "__main__":
    result = publish()
    icon = "🟢" if result["status"] == "GREEN" else "🟡" if result["status"] == "YELLOW" else "🔴"
    print(f"{icon} Infrastructure: {result['status']}")
    print(f"  Inventory: {result['inventory']['nodes_ok']}/{result['inventory']['nodes_total']} nodes")
    print(f"  Proxmox: {result['proxmox']['files_exported']} files exported")
    print(f"  OPNsense: {'✅ fresh' if result['opnsense']['fresh'] else '⚠️ stale/missing'}")
