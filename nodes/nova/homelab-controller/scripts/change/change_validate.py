#!/usr/bin/env python3
"""Run validation checks for a change: connectivity, ports, health, cluster."""
import json
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CHANGES_DIR = ROOT / "changes"

CHECKS = [
    {"name": "nova_ssh", "host": "10.1.1.21", "port": 22},
    {"name": "mira_ssh", "host": "10.1.1.22", "port": 22},
    {"name": "orin_ssh", "host": "10.1.1.23", "port": 22},
    {"name": "opnsense_ssh", "host": "10.1.1.1", "port": 22},
    {"name": "proxmox1_webui", "host": "10.1.1.2", "port": 8006},
    {"name": "proxmox2_webui", "host": "10.1.1.4", "port": 8006},
    {"name": "proxmox3_webui", "host": "10.1.1.5", "port": 8006},
    {"name": "dashboard", "host": "10.1.1.21", "port": 8080},
]


def check_port(host, port, timeout=3):
    try:
        s = socket.socket()
        s.settimeout(timeout)
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False


def validate_change(change_id):
    change_dir = CHANGES_DIR / change_id
    if not change_dir.exists():
        print(f"[ERROR] Change not found: {change_id}")
        return 1

    results = {
        "change_id": change_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": [],
        "passed": 0,
        "failed": 0,
        "all_passed": False,
    }

    for check in CHECKS:
        ok = check_port(check["host"], check["port"])
        results["checks"].append({
            "name": check["name"],
            "host": check["host"],
            "port": check["port"],
            "passed": ok,
        })
        if ok:
            results["passed"] += 1
        else:
            results["failed"] += 1
        icon = "[OK]" if ok else "[FAIL]"
        print(f"  {icon} {check['name']} ({check['host']}:{check['port']})")

    results["all_passed"] = results["failed"] == 0

    with open(change_dir / "validation.json", "w") as f:
        json.dump(results, f, indent=2)

    # Markdown
    lines = [
        f"# Validation -- {change_id}",
        f"",
        f"Passed: **{results['passed']}** / Failed: **{results['failed']}**",
        f"",
        "| Check | Host:Port | Status |",
        "|-------|-----------|--------|",
    ]
    for c in results["checks"]:
        status = "PASS" if c["passed"] else "**FAIL**"
        lines.append(f"| {c['name']} | {c['host']}:{c['port']} | {status} |")

    with open(change_dir / "validation.md", "w") as f:
        f.write("\n".join(lines) + "\n")

    # Update change record
    change_file = change_dir / "change.json"
    if change_file.exists():
        with open(change_file) as f:
            record = json.load(f)
        record["phases"]["validated"] = datetime.now(timezone.utc).isoformat()
        record["status"] = "validated" if results["all_passed"] else "validation_failed"
        with open(change_file, "w") as f:
            json.dump(record, f, indent=2)

    status = "ALL PASSED" if results["all_passed"] else f"{results['failed']} FAILED"
    print(f"\n  Validation: {status}")
    return 0 if results["all_passed"] else 1


def main():
    change_id = sys.argv[1] if len(sys.argv) > 1 else None
    if not change_id:
        if CHANGES_DIR.exists():
            dirs = sorted([d for d in CHANGES_DIR.iterdir() if d.is_dir() and d.name.startswith("CHG-")])
            if dirs:
                change_id = dirs[-1].name
    if not change_id:
        print("[ERROR] No change ID")
        return 1
    return validate_change(change_id)


if __name__ == "__main__":
    sys.exit(main())
