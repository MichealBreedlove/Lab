#!/usr/bin/env python3
"""P40 — Synthetic Checks: probe infrastructure endpoints for availability."""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "verification_policy.json"
ARTIFACTS = ROOT / "artifacts" / "verification"


def load_policy():
    with open(CONFIG) as f:
        return json.load(f)


def run_ssh_check(check, timeout=30):
    host = check["host"]
    user = check.get("user", "micheal")
    cmd = check.get("command", "uptime")
    key = str(Path("~/.ssh/id_ed25519").expanduser())
    start = time.time()
    try:
        r = subprocess.run(
            ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=10",
             "-i", key, f"{user}@{host}", cmd],
            capture_output=True, text=True, timeout=timeout
        )
        elapsed = round(time.time() - start, 2)
        return {"pass": r.returncode == 0, "latency_s": elapsed, "output": r.stdout.strip()[:100]}
    except Exception as e:
        return {"pass": False, "latency_s": round(time.time() - start, 2), "error": str(e)[:100]}


def run_command_check(check, timeout=30):
    cmd = check["command"]
    start = time.time()
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        elapsed = round(time.time() - start, 2)
        return {"pass": r.returncode == 0, "latency_s": elapsed, "output": r.stdout.strip()[:100]}
    except Exception as e:
        return {"pass": False, "latency_s": round(time.time() - start, 2), "error": str(e)[:100]}


def run_http_check(check, timeout=30):
    url = check["url"]
    expected = check.get("expect_status", 200)
    start = time.time()
    try:
        r = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "--max-time", str(timeout), url],
            capture_output=True, text=True, timeout=timeout + 5
        )
        elapsed = round(time.time() - start, 2)
        status = int(r.stdout.strip()) if r.stdout.strip().isdigit() else 0
        return {"pass": status == expected, "latency_s": elapsed, "status_code": status}
    except Exception as e:
        return {"pass": False, "latency_s": round(time.time() - start, 2), "error": str(e)[:100]}


def run_checks():
    policy = load_policy()
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    timeout = policy["synthetic_checks"].get("timeout_seconds", 30)
    results = []

    for check in policy["synthetic_checks"]["checks"]:
        name = check["name"]
        ctype = check["type"]

        if ctype == "ssh":
            result = run_ssh_check(check, timeout)
        elif ctype == "http":
            result = run_http_check(check, timeout)
        else:
            result = run_command_check(check, timeout)

        result["name"] = name
        result["type"] = ctype
        results.append(result)

    total = len(results)
    passing = sum(1 for r in results if r["pass"])

    report = {
        "timestamp": timestamp,
        "checks": results,
        "summary": {"total": total, "passing": passing, "failing": total - passing},
        "pass": passing == total,
    }

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    with open(ARTIFACTS / "synthetic_latest.json", "w") as f:
        json.dump(report, f, indent=2)

    # Append to history
    history = ARTIFACTS / "history.jsonl"
    with open(history, "a") as f:
        f.write(json.dumps({"timestamp": timestamp, "type": "synthetic", "passing": passing, "total": total}) + "\n")

    return report


def main():
    parser = argparse.ArgumentParser(description="Synthetic Checks")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = run_checks()

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        icon = "✅" if report["pass"] else "❌"
        s = report["summary"]
        print(f"{icon} Synthetic checks: {s['passing']}/{s['total']} passing")
        for c in report["checks"]:
            ci = "✅" if c["pass"] else "❌"
            print(f"  {ci} {c['name']} ({c['latency_s']}s)")

    sys.exit(0)


if __name__ == "__main__":
    main()
