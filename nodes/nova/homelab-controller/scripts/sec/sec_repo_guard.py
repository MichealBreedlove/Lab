#!/usr/bin/env python3
"""P38 — Repo Guard: pre-commit hook that blocks pushes if secretscan fails or forbidden files appear."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

FORBIDDEN_PATTERNS = [
    "*.pem", "*.key", "*.p12", "*.pfx",
    ".env", "*.env.local",
    "id_rsa", "id_ed25519", "id_ecdsa",
]


def check_staged_files():
    """Check git staged files for forbidden patterns."""
    try:
        r = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, cwd=str(ROOT)
        )
        staged = r.stdout.strip().splitlines() if r.returncode == 0 else []
    except Exception:
        staged = []

    violations = []
    for f in staged:
        name = Path(f).name
        for pattern in FORBIDDEN_PATTERNS:
            if pattern.startswith("*"):
                if name.endswith(pattern[1:]):
                    violations.append({"file": f, "reason": f"matches {pattern}"})
            else:
                if name == pattern:
                    violations.append({"file": f, "reason": f"forbidden file: {pattern}"})

    return violations


def run_secretscan():
    """Run the secret scanner."""
    try:
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "sec" / "sec_secretscan.py"), "--json"],
            capture_output=True, text=True, cwd=str(ROOT)
        )
        result = json.loads(r.stdout)
        return result.get("pass", False), result.get("violations", [])
    except Exception as e:
        return False, [{"error": str(e)}]


def guard():
    """Run all pre-commit checks."""
    issues = []

    # Check forbidden files
    forbidden = check_staged_files()
    if forbidden:
        issues.extend(forbidden)

    # Run secret scan
    scan_ok, scan_violations = run_secretscan()
    if not scan_ok:
        issues.extend(scan_violations)

    if issues:
        print("🚫 Repo guard BLOCKED commit:")
        for issue in issues:
            if "file" in issue:
                print(f"  ❌ {issue['file']}: {issue.get('reason', issue.get('pattern', 'violation'))}")
            elif "error" in issue:
                print(f"  ❌ Error: {issue['error']}")
        return False

    print("✅ Repo guard: all checks passed")
    return True


if __name__ == "__main__":
    sys.exit(0 if guard() else 1)
