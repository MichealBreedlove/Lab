#!/usr/bin/env python3
"""P31 — Bootstrap Preflight: verify target node is reachable, SSH works, and prerequisites met."""

import argparse
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "artifacts" / "bootstrap"
CONFIG_DIR = ROOT / "config"


def load_json(path):
    with open(path) as f:
        return json.load(f)


def check_ssh(host, user, key_path, timeout=15):
    """Test SSH connectivity to target node."""
    key_path = str(Path(key_path).expanduser())
    try:
        r = subprocess.run(
            ["ssh", "-o", "StrictHostKeyChecking=accept-new",
             "-o", f"ConnectTimeout={timeout}",
             "-i", key_path,
             f"{user}@{host}", "echo ok"],
            capture_output=True, text=True, timeout=timeout + 5
        )
        return r.returncode == 0, r.stdout.strip()
    except Exception as e:
        return False, str(e)


def check_port(host, port, timeout=5):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        result = s.connect_ex((host, port))
        s.close()
        return result == 0
    except Exception:
        return False


def run_preflight(node_name):
    policy = load_json(CONFIG_DIR / "bootstrap_policy.json")
    profiles = load_json(CONFIG_DIR / "node_profiles.json")

    node_cfg = profiles.get("nodes", {}).get(node_name)
    if not node_cfg:
        return {"error": f"node '{node_name}' not found in node_profiles.json", "pass": False}

    profile = profiles["profiles"].get(node_cfg.get("profile", ""))
    if not profile:
        return {"error": f"profile '{node_cfg.get('profile')}' not found", "pass": False}

    ip = node_cfg["ip"]
    platform = node_cfg.get("platform", "linux")

    result = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "node": node_name,
        "ip": ip,
        "platform": platform,
        "profile": node_cfg.get("profile"),
        "checks": {},
    }

    # Check network reachability (ping)
    if policy.get("require_network_reachable", True):
        try:
            r = subprocess.run(
                ["ping", "-c", "1", "-W", "3", ip],
                capture_output=True, timeout=10
            )
            result["checks"]["network"] = r.returncode == 0
        except Exception:
            result["checks"]["network"] = False

    # Check SSH (Linux only)
    if platform == "linux" and policy.get("require_ssh_key_auth", True):
        ssh_ok, ssh_msg = check_ssh(
            ip, policy.get("ssh_user", "micheal"),
            policy.get("ssh_key_path", "~/.ssh/id_ed25519"),
            policy.get("ssh_timeout_sec", 15)
        )
        result["checks"]["ssh"] = ssh_ok
        result["checks"]["ssh_detail"] = ssh_msg

    # Check if SSH port is open
    result["checks"]["ssh_port"] = check_port(ip, 22)

    # Check if node already has OpenClaw running
    oc_port = policy.get("openclaw", {}).get("gateway_port", 18789)
    result["checks"]["openclaw_already_running"] = check_port(ip, oc_port)

    # Policy checks
    result["checks"]["policy_enabled"] = policy.get("enabled", False)
    result["checks"]["profile_valid"] = profile is not None

    # Summary
    critical_checks = ["network", "ssh_port", "policy_enabled", "profile_valid"]
    if platform == "linux":
        critical_checks.append("ssh")
    result["pass"] = all(result["checks"].get(c, False) for c in critical_checks)

    # Write artifact
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(ARTIFACTS_DIR / f"preflight_{node_name}.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


def main():
    parser = argparse.ArgumentParser(description="Bootstrap Preflight")
    parser.add_argument("--node", required=True, help="Target node name")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = run_preflight(args.node)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        icon = "✅" if result.get("pass") else "❌"
        print(f"{icon} Bootstrap preflight: {'PASS' if result.get('pass') else 'FAIL'}")
        print(f"  Node: {result.get('node')} ({result.get('ip')}) — {result.get('profile')}")
        for check, val in result.get("checks", {}).items():
            if check.endswith("_detail"):
                continue
            ci = "✅" if val else "❌"
            print(f"  {ci} {check}: {val}")
        if "error" in result:
            print(f"  ❌ Error: {result['error']}")

    sys.exit(0 if result.get("pass") else 1)


if __name__ == "__main__":
    main()
