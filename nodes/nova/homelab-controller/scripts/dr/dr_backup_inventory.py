#!/usr/bin/env python3
"""D4 — DR Backup Inventory: captures what's installed/running on a node into JSON."""

import argparse
import hashlib
import json
import os
import platform
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "artifacts" / "dr"


def detect_node():
    hostname = socket.gethostname().lower()
    for name in ["jasper", "nova", "mira", "orin"]:
        if name in hostname:
            return name
    return hostname


def run_cmd(cmd, timeout=15):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def hash_file(path):
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]
    except Exception:
        return None


def inventory_linux(node):
    inv = {"platform": "linux", "node": node}

    # systemd user units
    units_raw = run_cmd(["systemctl", "--user", "list-units", "--type=service,timer", "--no-pager", "--plain", "--no-legend"])
    inv["systemd_user_units"] = units_raw.splitlines() if units_raw else []

    # open ports
    ports_raw = run_cmd(["ss", "-ltnp"])
    if ports_raw:
        inv["open_ports"] = [l.strip() for l in ports_raw.splitlines()[1:] if l.strip()]
    else:
        ports_raw = run_cmd(["netstat", "-tlnp"])
        inv["open_ports"] = [l.strip() for l in ports_raw.splitlines()[1:] if l.strip()] if ports_raw else []

    # installed packages (count + key packages)
    dpkg_raw = run_cmd(["dpkg", "-l"])
    if dpkg_raw:
        lines = [l for l in dpkg_raw.splitlines() if l.startswith("ii")]
        inv["package_count"] = len(lines)
        key_pkgs = ["python3", "git", "ansible", "openssh-server", "jq", "curl"]
        inv["key_packages"] = {p: any(p in l for l in lines) for p in key_pkgs}
    else:
        inv["package_count"] = 0
        inv["key_packages"] = {}

    # OpenClaw version
    oc_ver = run_cmd(["openclaw", "--version"]) or run_cmd(["openclaw", "version"])
    inv["openclaw_version"] = oc_ver

    # Config hashes
    config_files = [
        Path.home() / ".openclaw" / "openclaw.json",
        ROOT / "config" / "slo_policy.json",
        ROOT / "config" / "slo_catalog.json",
        ROOT / "config" / "dr_policy.json",
    ]
    inv["config_hashes"] = {}
    for cf in config_files:
        h = hash_file(cf)
        if h:
            inv["config_hashes"][cf.name] = h

    return inv


def inventory_windows(node):
    inv = {"platform": "windows", "node": node}

    # OpenClaw version
    oc_ver = run_cmd(["openclaw", "--version"]) or run_cmd(["openclaw", "version"])
    inv["openclaw_version"] = oc_ver

    # Gateway status
    gw_status = run_cmd(["openclaw", "gateway", "status"])
    inv["gateway_status"] = gw_status

    # Port check
    inv["port_checks"] = {}
    for port in [18789, 11434]:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            result = s.connect_ex(("127.0.0.1", port))
            inv["port_checks"][str(port)] = result == 0
            s.close()
        except Exception:
            inv["port_checks"][str(port)] = False

    # Scheduled tasks
    tasks_raw = run_cmd(["schtasks", "/query", "/fo", "csv", "/nh"])
    if tasks_raw:
        inv["scheduled_tasks"] = [l.split(",")[0].strip('"') for l in tasks_raw.splitlines() if l.strip()]
    else:
        inv["scheduled_tasks"] = []

    # Key files
    key_files = [
        Path.home() / ".openclaw" / "openclaw.json",
    ]
    inv["key_files"] = {str(f): f.exists() for f in key_files}

    return inv


def run_inventory(node=None):
    if node is None:
        node = detect_node()

    plat = platform.system().lower()
    if plat == "windows" or node == "jasper":
        inv = inventory_windows(node)
    else:
        inv = inventory_linux(node)

    inv["timestamp"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    inv["hostname"] = socket.gethostname()

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ARTIFACTS_DIR / f"inventory_{node}.json"
    with open(out_path, "w") as f:
        json.dump(inv, f, indent=2)

    return inv


def main():
    parser = argparse.ArgumentParser(description="DR Backup Inventory")
    parser.add_argument("--node", help="Node name (auto-detect if omitted)")
    parser.add_argument("--json", action="store_true", help="JSON output only")
    args = parser.parse_args()

    inv = run_inventory(node=args.node)

    if args.json:
        print(json.dumps(inv, indent=2))
    else:
        print(f"📋 Inventory: {inv['node']} ({inv['platform']})")
        print(f"  Hostname: {inv['hostname']}")
        print(f"  OpenClaw: {inv.get('openclaw_version', 'unknown')}")
        if inv["platform"] == "linux":
            print(f"  Packages: {inv.get('package_count', '?')}")
            print(f"  Units: {len(inv.get('systemd_user_units', []))}")
            print(f"  Open ports: {len(inv.get('open_ports', []))}")
        else:
            ports = inv.get("port_checks", {})
            print(f"  Ports: {', '.join(f'{k}={'✅' if v else '❌'}' for k, v in ports.items())}")
            print(f"  Tasks: {len(inv.get('scheduled_tasks', []))}")
        print(f"  Config hashes: {len(inv.get('config_hashes', {}))}")
        print(f"  Written: artifacts/dr/inventory_{inv['node']}.json")

    sys.exit(0)


if __name__ == "__main__":
    main()
