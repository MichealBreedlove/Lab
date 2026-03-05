#!/usr/bin/env python3
"""P40 — Canary Checks: lightweight probes that validate core system functions."""

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


def run_canary(check):
    name = check["name"]
    ctype = check["type"]
    start = time.time()

    try:
        if ctype == "file_write":
            path = Path(check["path"])
            content = check.get("content", "canary_ok")
            path.write_text(content)
            readback = path.read_text()
            path.unlink(missing_ok=True)
            elapsed = round(time.time() - start, 3)
            return {"name": name, "pass": readback == content, "latency_s": elapsed}
        elif ctype == "command":
            r = subprocess.run(check["command"], shell=True, capture_output=True, text=True, timeout=15)
            elapsed = round(time.time() - start, 3)
            return {"name": name, "pass": r.returncode == 0 and "fail" not in r.stdout.lower(), "latency_s": elapsed}
        else:
            return {"name": name, "pass": False, "error": f"unknown type: {ctype}"}
    except Exception as e:
        return {"name": name, "pass": False, "error": str(e)[:100], "latency_s": round(time.time() - start, 3)}


def run_canaries():
    policy = load_policy()
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    results = []

    for check in policy.get("canary_checks", {}).get("checks", []):
        results.append(run_canary(check))

    total = len(results)
    passing = sum(1 for r in results if r["pass"])

    report = {
        "timestamp": timestamp,
        "checks": results,
        "summary": {"total": total, "passing": passing},
        "pass": passing == total,
    }

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    with open(ARTIFACTS / "canary_latest.json", "w") as f:
        json.dump(report, f, indent=2)

    with open(ARTIFACTS / "history.jsonl", "a") as f:
        f.write(json.dumps({"timestamp": timestamp, "type": "canary", "passing": passing, "total": total}) + "\n")

    return report


if __name__ == "__main__":
    report = run_canaries()
    icon = "✅" if report["pass"] else "❌"
    print(f"{icon} Canary checks: {report['summary']['passing']}/{report['summary']['total']}")
    for c in report["checks"]:
        ci = "✅" if c["pass"] else "❌"
        print(f"  {ci} {c['name']}")
