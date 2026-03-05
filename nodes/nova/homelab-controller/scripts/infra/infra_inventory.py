#!/usr/bin/env python3
"""P37 — Infrastructure Inventory: collect host info from all nodes via SSH."""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "artifacts" / "infra"
CONFIG_DIR = ROOT / "config"


def load_json(path):
    with open(path) as f:
        return json.load(f)


def ssh_cmd(host, user, key_path, command, timeout=30):
    key_path = str(Path(key_path).expanduser())
    try:
        r = subprocess.run(
            ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=10",
             "-i", key_path, f"{user}@{host}", command],
            capture_output=True, text=True, timeout=timeout
        )
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def collect_node(name, ip, user, key="~/.ssh/id_ed25519"):
    """Collect inventory from a Linux node."""
    inv = {"node": name, "ip": ip, "platform": "linux", "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    inv["hostname"] = ssh_cmd(ip, user, key, "hostname") or name
    inv["os"] = ssh_cmd(ip, user, key, "cat /etc/os-release | grep PRETTY_NAME | cut -d'\"' -f2")
    inv["kernel"] = ssh_cmd(ip, user, key, "uname -r")
    inv["uptime"] = ssh_cmd(ip, user, key, "uptime -p")
    inv["cpu_model"] = ssh_cmd(ip, user, key, "grep 'model name' /proc/cpuinfo | head -1 | cut -d: -f2 | xargs")
    inv["cpu_cores"] = ssh_cmd(ip, user, key, "nproc")
    inv["memory_total"] = ssh_cmd(ip, user, key, "free -h | awk '/Mem:/ {print $2}'")

    # Disks
    disk_out = ssh_cmd(ip, user, key, "lsblk -d -o NAME,SIZE,TYPE | grep disk")
    inv["disks"] = disk_out.splitlines() if disk_out else []

    # ZFS pools
    zfs_out = ssh_cmd(ip, user, key, "zpool list -H -o name,size,alloc,free,health 2>/dev/null")
    inv["zfs_pools"] = zfs_out.splitlines() if zfs_out else []

    # Network interfaces
    nic_out = ssh_cmd(ip, user, key, "ip -brief addr show | grep -v '^lo'")
    inv["network_interfaces"] = nic_out.splitlines() if nic_out else []

    # Open ports (listening)
    ports_out = ssh_cmd(ip, user, key, "ss -tlnp 2>/dev/null | tail -n +2 | awk '{print $4}' | sort -u")
    inv["listening_ports"] = ports_out.splitlines() if ports_out else []

    # Services
    svc_out = ssh_cmd(ip, user, key, "systemctl --user list-units --type=service --state=running --no-pager --no-legend 2>/dev/null | head -15")
    inv["user_services"] = svc_out.splitlines() if svc_out else []

    return inv


def collect_all():
    targets = load_json(CONFIG_DIR / "infra_targets.json")
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    results = {"timestamp": timestamp, "nodes": {}}

    for name, cfg in targets.get("nodes", {}).items():
        if cfg.get("platform") != "linux":
            results["nodes"][name] = {"status": "skipped", "platform": cfg.get("platform")}
            continue
        inv = collect_node(name, cfg["ip"], cfg.get("ssh_user", "micheal"))
        results["nodes"][name] = inv

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(ARTIFACTS_DIR / "inventory_latest.json", "w") as f:
        json.dump(results, f, indent=2)

    # Per-node files
    for name, data in results["nodes"].items():
        if data.get("status") == "skipped":
            continue
        with open(ARTIFACTS_DIR / f"inventory_{name}.json", "w") as f:
            json.dump(data, f, indent=2)

    return results


def main():
    parser = argparse.ArgumentParser(description="Infrastructure Inventory")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    results = collect_all()

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"📋 Infrastructure Inventory ({results['timestamp'][:19]})")
        for name, data in results["nodes"].items():
            if data.get("status") == "skipped":
                print(f"  ⏭️  {name}: {data.get('platform')} (skipped)")
                continue
            print(f"  🖥️  {name} ({data.get('ip')})")
            print(f"      OS: {data.get('os', '?')} | Kernel: {data.get('kernel', '?')}")
            print(f"      CPU: {data.get('cpu_model', '?')} ({data.get('cpu_cores', '?')} cores)")
            print(f"      RAM: {data.get('memory_total', '?')} | Uptime: {data.get('uptime', '?')}")

    sys.exit(0)


if __name__ == "__main__":
    main()
