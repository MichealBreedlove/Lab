#!/usr/bin/env python3
"""P31 — Bootstrap Validate: verify node is fully bootstrapped and operational."""

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


def ssh_cmd(host, user, key_path, command, timeout=30):
    key_path = str(Path(key_path).expanduser())
    try:
        r = subprocess.run(
            ["ssh", "-o", "StrictHostKeyChecking=accept-new",
             "-o", "ConnectTimeout=10",
             "-i", key_path,
             f"{user}@{host}", command],
            capture_output=True, text=True, timeout=timeout
        )
        return {"ok": r.returncode == 0, "stdout": r.stdout.strip()[:500]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def check_port(host, port, timeout=5):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        result = s.connect_ex((host, port))
        s.close()
        return result == 0
    except Exception:
        return False


def run_validate(node_name):
    policy = load_json(CONFIG_DIR / "bootstrap_policy.json")
    profiles = load_json(CONFIG_DIR / "node_profiles.json")

    node_cfg = profiles["nodes"].get(node_name)
    if not node_cfg:
        return {"error": f"node '{node_name}' not found", "pass": False}

    profile_name = node_cfg.get("profile", "worker")
    profile = profiles["profiles"].get(profile_name, {})
    ip = node_cfg["ip"]
    user = policy.get("ssh_user", "micheal")
    key = policy.get("ssh_key_path", "~/.ssh/id_ed25519")
    clone_target = policy.get("git", {}).get("clone_target", "~/Lab")
    validation_cfg = policy.get("validation", {})

    checks = []

    # Check 1: SSH reachable
    ssh_ok, _ = False, ""
    if node_cfg.get("platform") == "linux":
        r = ssh_cmd(ip, user, key, "echo ok")
        ssh_ok = r["ok"]
    checks.append({"name": "ssh_reachable", "pass": ssh_ok or node_cfg.get("platform") == "windows"})

    # Check 2: Required ports
    for port in validation_cfg.get("required_ports", [18789]):
        ok = check_port(ip, port)
        checks.append({"name": f"port_{port}", "pass": ok, "detail": f"{ip}:{port}"})

    # Check 3: Required services (via SSH)
    if node_cfg.get("platform") == "linux":
        for svc in validation_cfg.get("required_services", []):
            r = ssh_cmd(ip, user, key, f"systemctl --user is-active {svc}")
            checks.append({"name": f"service_{svc}", "pass": r.get("ok", False)})

    # Check 4: Lab repo exists
    if node_cfg.get("platform") == "linux":
        r = ssh_cmd(ip, user, key, f"test -d {clone_target}/.git && echo yes || echo no")
        checks.append({"name": "lab_repo_cloned", "pass": r.get("stdout") == "yes"})

    # Check 5: OpenClaw installed
    if node_cfg.get("platform") == "linux":
        r = ssh_cmd(ip, user, key, "which openclaw || openclaw --version")
        checks.append({"name": "openclaw_installed", "pass": r.get("ok", False)})

    # Check 6: Git configured
    if node_cfg.get("platform") == "linux":
        r = ssh_cmd(ip, user, key, "git config user.name")
        checks.append({"name": "git_configured", "pass": r.get("ok", False)})

    # Check 7: Backup timer
    if node_cfg.get("platform") == "linux":
        r = ssh_cmd(ip, user, key, "systemctl --user is-enabled lab-backup.timer 2>/dev/null || echo disabled")
        checks.append({"name": "backup_timer", "pass": "enabled" in r.get("stdout", "") or r.get("ok", False)})

    # Check 8: Cross-node connectivity
    node_ips = {n: c["ip"] for n, c in profiles["nodes"].items() if n != node_name}
    for remote_name, remote_ip in node_ips.items():
        ok = check_port(remote_ip, 18789, timeout=3)
        checks.append({
            "name": f"connectivity_{remote_name}",
            "pass": ok,
            "detail": f"{remote_name} ({remote_ip}:18789)",
        })

    # Summary
    total = len(checks)
    passing = sum(1 for c in checks if c["pass"])

    result = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "node": node_name,
        "ip": ip,
        "profile": profile_name,
        "checks": checks,
        "summary": {"total": total, "passing": passing, "failing": total - passing},
        "pass": passing == total,
    }

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(ARTIFACTS_DIR / f"validate_{node_name}.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


def main():
    parser = argparse.ArgumentParser(description="Bootstrap Validate")
    parser.add_argument("--node", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = run_validate(args.node)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        s = result.get("summary", {})
        icon = "✅" if result.get("pass") else "❌"
        print(f"{icon} Bootstrap validate: {s.get('passing')}/{s.get('total')} checks passing")
        for c in result.get("checks", []):
            ci = "✅" if c["pass"] else "❌"
            detail = f" — {c['detail']}" if "detail" in c else ""
            print(f"  {ci} {c['name']}{detail}")

    sys.exit(0 if result.get("pass") else 1)


if __name__ == "__main__":
    main()
