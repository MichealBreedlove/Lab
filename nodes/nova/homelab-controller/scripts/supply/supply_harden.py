#!/usr/bin/env python3
"""P41 — Hardening Checks: enforce script hygiene, file permissions, banned patterns."""

import json
import os
import re
import stat
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "supply_chain_policy.json"
ARTIFACTS = ROOT / "artifacts" / "supply_chain"


def load_policy():
    with open(CONFIG) as f:
        return json.load(f)


def check_shebang(path):
    """Check that scripts have proper shebangs."""
    try:
        first_line = path.read_text().splitlines()[0] if path.stat().st_size > 0 else ""
        if path.suffix == ".py":
            return first_line.startswith("#!/usr/bin/env python3") or first_line.startswith("#!")
        elif path.suffix == ".sh":
            return first_line.startswith("#!/usr/bin/env bash") or first_line.startswith("#!/bin/bash")
        return True
    except Exception:
        return False


def check_bash_safety(path):
    """Check bash scripts use set -euo pipefail."""
    try:
        content = path.read_text()
        return "set -euo pipefail" in content or "set -eu" in content
    except Exception:
        return False


def check_banned_commands(path, banned):
    """Check for banned command patterns."""
    try:
        content = path.read_text()
        found = []
        for pattern in banned:
            if pattern.lower() in content.lower():
                found.append(pattern)
        return found
    except Exception:
        return []


def run_hardening():
    policy = load_policy()
    hardening = policy.get("hardening", {})
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    max_size_kb = hardening.get("max_script_size_kb", 100)
    banned = hardening.get("banned_commands", [])
    checks = []

    scripts_dir = ROOT / "scripts"
    if not scripts_dir.exists():
        return {"timestamp": timestamp, "checks": [], "pass": True}

    for f in sorted(scripts_dir.rglob("*")):
        if f.is_dir() or f.suffix not in (".py", ".sh"):
            continue
        if "__pycache__" in f.parts:
            continue

        rel = str(f.relative_to(ROOT))
        file_checks = {"file": rel, "issues": []}

        # Shebang check
        if hardening.get("enforce_shebang", True) and not check_shebang(f):
            file_checks["issues"].append("missing_shebang")

        # Bash safety check
        if f.suffix == ".sh" and hardening.get("enforce_set_euo_pipefail", True):
            if not check_bash_safety(f):
                file_checks["issues"].append("missing_set_euo_pipefail")

        # Size check
        size_kb = f.stat().st_size / 1024
        if size_kb > max_size_kb:
            file_checks["issues"].append(f"oversized_{round(size_kb)}kb")

        # Banned commands
        found_banned = check_banned_commands(f, banned)
        if found_banned:
            file_checks["issues"].extend([f"banned:{b}" for b in found_banned])

        file_checks["pass"] = len(file_checks["issues"]) == 0
        checks.append(file_checks)

    total = len(checks)
    passing = sum(1 for c in checks if c["pass"])
    failing_files = [c for c in checks if not c["pass"]]

    report = {
        "timestamp": timestamp,
        "files_checked": total,
        "passing": passing,
        "failing": total - passing,
        "failing_files": failing_files,
        "pass": len(failing_files) == 0,
    }

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    with open(ARTIFACTS / "hardening_latest.json", "w") as f_out:
        json.dump(report, f_out, indent=2)

    return report


if __name__ == "__main__":
    report = run_hardening()
    icon = "✅" if report["pass"] else "❌"
    print(f"{icon} Hardening: {report['passing']}/{report['files_checked']} scripts pass")
    for f in report.get("failing_files", []):
        print(f"  ❌ {f['file']}: {', '.join(f['issues'])}")
