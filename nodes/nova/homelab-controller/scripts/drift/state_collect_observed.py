#!/usr/bin/env python3
"""Collect observed state from all nodes via SSH into state/observed/."""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG = ROOT / "config" / "desired_state.json"
OBSERVED_DIR = ROOT / "state" / "observed"


def ssh_cmd(host, user, cmd, timeout=10):
    """Run command on remote host via SSH, return stdout or None."""
    try:
        # If this is the local host, run directly
        import socket
        local_ips = []
        try:
            local_ips = [a[4][0] for a in socket.getaddrinfo(socket.gethostname(), None)]
            local_ips.append("127.0.0.1")
        except Exception:
            pass

        if host in local_ips or socket.gethostname().lower() == user.lower():
            r = subprocess.run(
                ["bash", "-c", cmd],
                capture_output=True, text=True, timeout=timeout
            )
            return r.stdout.strip() if r.returncode == 0 else None

        r = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
             f"{user}@{host}", cmd],
            capture_output=True, text=True, timeout=timeout
        )
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def collect_node(name, spec):
    """Collect observed state for a single node."""
    ip = spec["ip"]
    user = spec["user"]
    node_dir = OBSERVED_DIR / name
    node_dir.mkdir(parents=True, exist_ok=True)

    observed = {
        "node": name,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ip": ip,
        "reachable": False,
        "services": {},
        "ports": {},
        "packages": {},
        "ssh_config": {},
        "firewall": {},
    }

    # Test connectivity
    hostname = ssh_cmd(ip, user, "hostname")
    if hostname is None:
        observed["reachable"] = False
        with open(node_dir / "observed.json", "w") as f:
            json.dump(observed, f, indent=2)
        print(f"  [WARN] {name} ({ip}): unreachable")
        return observed

    observed["reachable"] = True
    observed["hostname"] = hostname

    # Check services
    for svc in spec.get("services", []):
        status = ssh_cmd(ip, user, f"systemctl is-active {svc} 2>/dev/null || echo inactive")
        observed["services"][svc] = status or "unknown"

    # Check ports
    for port in spec.get("ports", []):
        result = ssh_cmd(ip, user, f"ss -tlnp | grep -q ':{port} ' && echo open || echo closed")
        observed["ports"][str(port)] = result or "unknown"

    # Check packages
    for pkg in spec.get("packages", []):
        result = ssh_cmd(ip, user, f"which {pkg} >/dev/null 2>&1 && echo installed || echo missing")
        observed["packages"][pkg] = result or "unknown"

    # Check SSH config
    for key in spec.get("ssh_config", {}):
        val = ssh_cmd(ip, user, f"sudo sshd -T 2>/dev/null | grep -i '^{key.lower()} ' | awk '{{print $2}}'")
        observed["ssh_config"][key] = val or "unknown"

    # Check firewall (ufw)
    fw_spec = spec.get("firewall", {})
    if fw_spec.get("ufw_enabled"):
        ufw_status = ssh_cmd(ip, user, "sudo ufw status | head -1")
        observed["firewall"]["ufw_active"] = "active" in (ufw_status or "").lower()

    with open(node_dir / "observed.json", "w") as f:
        json.dump(observed, f, indent=2)

    print(f"  [OK] {name} ({ip}): collected")
    return observed


def collect_infrastructure(infra):
    """Collect infrastructure observed state."""
    infra_dir = OBSERVED_DIR / "infrastructure"
    infra_dir.mkdir(parents=True, exist_ok=True)

    observed = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "opnsense": {"reachable": False},
        "proxmox": {"nodes": {}},
    }

    # OPNsense (FreeBSD — use full path or fallback)
    opn = infra.get("opnsense", {})
    if opn.get("ip"):
        version = ssh_cmd(opn["ip"], "root", "/usr/local/sbin/opnsense-version 2>/dev/null || uname -r")
        observed["opnsense"]["reachable"] = version is not None
        observed["opnsense"]["version"] = version

    # Proxmox
    for pve_name, pve_spec in infra.get("proxmox", {}).get("nodes", {}).items():
        ip = pve_spec["ip"]
        pve_ver = ssh_cmd(ip, "root", "pveversion 2>/dev/null")
        observed["proxmox"]["nodes"][pve_name] = {
            "reachable": pve_ver is not None,
            "version": pve_ver,
        }

    with open(infra_dir / "observed.json", "w") as f:
        json.dump(observed, f, indent=2)

    return observed


def main():
    with open(CONFIG) as f:
        config = json.load(f)

    OBSERVED_DIR.mkdir(parents=True, exist_ok=True)
    print("Collecting observed state...")

    for name, spec in config.get("nodes", {}).items():
        collect_node(name, spec)

    collect_infrastructure(config.get("infrastructure", {}))

    print(f"[OK] Observed state written to {OBSERVED_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
