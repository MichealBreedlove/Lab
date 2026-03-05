#!/usr/bin/env python3
"""P41 — Provenance Tracker: record build environment and git state."""

import json
import platform
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts" / "supply_chain"


def git_cmd(args):
    try:
        r = subprocess.run(["git"] + args, capture_output=True, text=True, cwd=str(ROOT), timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def generate_provenance():
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    provenance = {
        "timestamp": timestamp,
        "build_environment": {
            "os": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version()[:80],
            "machine": platform.machine(),
            "python_version": platform.python_version(),
            "hostname": platform.node(),
        },
        "git": {
            "commit": git_cmd(["rev-parse", "HEAD"]),
            "branch": git_cmd(["rev-parse", "--abbrev-ref", "HEAD"]),
            "dirty": git_cmd(["status", "--porcelain"]) != "",
            "remote": git_cmd(["remote", "get-url", "origin"]),
            "tag": git_cmd(["describe", "--tags", "--always"]),
        },
        "controller": {
            "root": str(ROOT),
            "config_files": len(list((ROOT / "config").glob("*.json"))) if (ROOT / "config").exists() else 0,
            "script_dirs": [d.name for d in (ROOT / "scripts").iterdir() if d.is_dir()] if (ROOT / "scripts").exists() else [],
        },
    }

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    with open(ARTIFACTS / "provenance.json", "w") as f:
        json.dump(provenance, f, indent=2)

    return provenance


if __name__ == "__main__":
    p = generate_provenance()
    print(f"📋 Provenance recorded at {p['timestamp']}")
    print(f"  Git: {p['git']['commit'][:8]} on {p['git']['branch']} {'(dirty)' if p['git']['dirty'] else '(clean)'}")
    print(f"  Python: {p['build_environment']['python_version']} on {p['build_environment']['os']}")
