#!/usr/bin/env python3
"""P38 — Security Baseline Audit: check SSH config, sudoers, firewall, ports, weak services."""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "artifacts" / "security"
CONFIG_DIR = ROOT / "config"


def load_json(path):
    with open(path) as f:
        return json.load(f)


def ssh_cmd(host, user, key, command, timeout=15):
    key = str(Path(key).expanduser())
    try:
        r = subprocess.run(
            ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=10",
             "-i", key, f"{user}@{host}", command],
            capture_output=True, text=True, timeout=timeout
        )
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def audit_node(name, ip, user, key, baseline):
    """Audit a single Linux node."""
    checks = []

    # SSH config checks
    sshd = ssh_cmd(ip, user, key, "cat /etc/ssh/sshd_config 2>/dev/null")
    if sshd:
        for setting, expected in baseline.get("ssh_baseline", {}).items():
            setting_name = setting.replace("_", " ").title().replace(" ", "")
            # Convert to sshd_config format
            sshd_key = {"permit_root_login": "PermitRootLogin", "password_authentication": "PasswordAuthentication",
                        "pubkey_authentication": "PubkeyAuthentication", "protocol": "Protocol"}.get(setting, setting)
            if sshd_key in sshd:
                actual = ""
                for line in sshd.splitlines():
                    if line.strip().startswith(sshd_key):
                        actual = line.split()[-1] if len(line.split()) > 1 else ""
                        break
                checks.append({
                    "category": "ssh",
                    "check": sshd_key,
                    "expected": str(expected),
                    "actual": actual,
                    "pass": actual.lower() == str(expected).lower(),
                })
            else:
                checks.append({"category": "ssh", "check": sshd_key, "expected": str(expected), "actual": "not set", "pass": False})

    # Firewall status
    fw = ssh_cmd(ip, user, key, "sudo ufw status 2>/dev/null || sudo iptables -L -n 2>/dev/null | head -5")
    checks.append({"category": "firewall", "check": "firewall_active", "pass": bool(fw and "active" in fw.lower()), "detail": fw[:100]})

    # Open ports check
    ports = ssh_cmd(ip, user, key, "ss -tlnp 2>/dev/null | tail -n +2")
    port_count = len(ports.splitlines()) if ports else 0
    checks.append({"category": "ports", "check": "listening_ports", "value": port_count, "pass": port_count < 20, "detail": f"{port_count} listening ports"})

    # Sudoers sanity
    sudoers = ssh_cmd(ip, user, key, "sudo cat /etc/sudoers 2>/dev/null | grep -c NOPASSWD")
    nopasswd_count = int(sudoers) if sudoers.isdigit() else 0
    checks.append({"category": "sudoers", "check": "nopasswd_entries", "value": nopasswd_count, "pass": nopasswd_count <= 3, "detail": f"{nopasswd_count} NOPASSWD entries"})

    # Weak services check
    weak_services = ["telnet", "ftp", "rsh", "rlogin"]
    for svc in weak_services:
        running = ssh_cmd(ip, user, key, f"systemctl is-active {svc} 2>/dev/null")
        checks.append({"category": "weak_services", "check": f"{svc}_disabled", "pass": running != "active"})

    # Summary
    total = len(checks)
    passing = sum(1 for c in checks if c["pass"])
    score = round((passing / total) * 100) if total > 0 else 0

    return {
        "node": name, "ip": ip, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "checks": checks, "summary": {"total": total, "passing": passing, "score": score},
        "pass": score >= 80,
    }


def audit_all():
    policy = load_json(CONFIG_DIR / "security_policy.json")
    targets = load_json(CONFIG_DIR / "infra_targets.json")
    key = "~/.ssh/id_ed25519"
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    results = {"timestamp": timestamp, "nodes": {}}

    for name, cfg in targets.get("nodes", {}).items():
        if cfg.get("platform") != "linux":
            results["nodes"][name] = {"status": "skipped", "platform": cfg.get("platform")}
            continue
        audit = audit_node(name, cfg["ip"], cfg.get("ssh_user", "micheal"), key, policy)
        results["nodes"][name] = audit

        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        with open(ARTIFACTS_DIR / f"sec_audit_{name}.json", "w") as f:
            json.dump(audit, f, indent=2)

    # Write combined
    with open(ARTIFACTS_DIR / "sec_audit_latest.json", "w") as f:
        json.dump(results, f, indent=2)

    return results


def main():
    parser = argparse.ArgumentParser(description="Security Baseline Audit")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    results = audit_all()

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"🔒 Security Audit ({results['timestamp'][:19]})")
        for name, data in results["nodes"].items():
            if data.get("status") == "skipped":
                print(f"  ⏭️  {name}: {data.get('platform')} (skipped)")
                continue
            s = data.get("summary", {})
            icon = "✅" if data.get("pass") else "❌"
            print(f"  {icon} {name}: {s.get('score', 0)}% ({s.get('passing', 0)}/{s.get('total', 0)} checks)")

    sys.exit(0)


if __name__ == "__main__":
    main()
