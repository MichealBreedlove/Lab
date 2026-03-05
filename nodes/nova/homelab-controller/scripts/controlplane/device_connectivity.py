#!/usr/bin/env python3
"""P43 — Device Connectivity Scanner: check reachability of all homelab devices."""

import json
import socket
import subprocess
import sys
import time
from pathlib import Path

DEVICES = {
    "opnsense": {"ip": "10.1.1.1", "ports": [22, 443]},
    "proxmox-1": {"ip": "10.1.1.2", "ports": [22, 8006]},
    "proxmox-2": {"ip": "10.1.1.4", "ports": [22, 8006]},
    "proxmox-3": {"ip": "10.1.1.5", "ports": [22, 8006]},
    "nova": {"ip": "10.1.1.21", "ports": [22]},
    "mira": {"ip": "10.1.1.22", "ports": [22]},
    "orin": {"ip": "10.1.1.23", "ports": [22]},
    "jasper": {"ip": "10.1.1.150", "ports": [22]},
    "truenas": {"ip": "10.1.1.11", "ports": [22, 443]},
    "unifi-ap": {"ip": "10.1.1.19", "ports": [22]},
}


def check_port(ip, port, timeout=3):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def check_ping(ip, timeout=3):
    try:
        r = subprocess.run(
            ["ping", "-c", "1", "-W", str(timeout), ip],
            capture_output=True, timeout=timeout + 2
        )
        return r.returncode == 0
    except Exception:
        return False


def scan_all():
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    results = {"timestamp": timestamp, "devices": {}}

    for name, info in DEVICES.items():
        ip = info["ip"]
        device = {"ip": ip, "ping": check_ping(ip), "ports": {}}
        for port in info["ports"]:
            device["ports"][str(port)] = check_port(ip, port)
        device["reachable"] = device["ping"] or any(device["ports"].values())
        results["devices"][name] = device

    reachable = sum(1 for d in results["devices"].values() if d["reachable"])
    results["summary"] = {"total": len(DEVICES), "reachable": reachable}
    return results


if __name__ == "__main__":
    results = scan_all()

    if "--json" in sys.argv:
        print(json.dumps(results, indent=2))
    else:
        print(f"🔍 Device Connectivity ({results['timestamp'][:19]})")
        print(f"   {results['summary']['reachable']}/{results['summary']['total']} reachable\n")
        for name, d in results["devices"].items():
            icon = "✅" if d["reachable"] else "❌"
            ports = ", ".join(f"{p}:{'✓' if v else '✗'}" for p, v in d["ports"].items())
            print(f"  {icon} {name:15s} {d['ip']:15s} ping:{'✓' if d['ping'] else '✗'}  {ports}")
