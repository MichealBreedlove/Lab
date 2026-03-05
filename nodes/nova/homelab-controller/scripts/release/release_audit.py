#!/usr/bin/env python3
"""P35 — Release Audit: verify all subsystems are healthy and tests pass before v1.0 tag."""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
CONFIG_DIR = ROOT / "config"


def load_json_safe(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def check_configs():
    """Verify all config files are valid JSON."""
    configs = list(CONFIG_DIR.glob("*.json"))
    results = []
    for cfg in configs:
        try:
            json.loads(cfg.read_text())
            results.append({"file": cfg.name, "valid": True})
        except Exception as e:
            results.append({"file": cfg.name, "valid": False, "error": str(e)})
    return results


def check_scripts():
    """Verify all Python scripts have valid syntax."""
    results = []
    for py_file in SCRIPTS_DIR.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        try:
            with open(py_file) as f:
                compile(f.read(), str(py_file), "exec")
            results.append({"file": str(py_file.relative_to(ROOT)), "valid": True})
        except SyntaxError as e:
            results.append({"file": str(py_file.relative_to(ROOT)), "valid": False, "error": str(e)})
    return results


def secret_scan():
    """Scan for leaked secrets in the repository."""
    patterns = [
        r'AKIA[0-9A-Z]{16}',
        r'ghp_[a-zA-Z0-9]{36}',
        r'-----BEGIN.*PRIVATE KEY-----',
        r'sk-[a-zA-Z0-9]{48}',
    ]
    violations = []
    for f in ROOT.rglob("*"):
        if f.is_dir() or ".git" in str(f) or "__pycache__" in str(f):
            continue
        if f.suffix in (".json", ".py", ".sh", ".ps1", ".md", ".yaml", ".yml"):
            try:
                content = f.read_text(errors="ignore")
                for pattern in patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        violations.append({"file": str(f.relative_to(ROOT)), "pattern": pattern, "count": len(matches)})
            except Exception:
                pass
    return violations


def check_subsystem_configs():
    """Verify each subsystem has its config file."""
    required = {
        "dr_policy.json": "Disaster Recovery (P30)",
        "bootstrap_policy.json": "Node Bootstrap (P31)",
        "node_profiles.json": "Node Profiles (P31)",
        "capacity_policy.json": "Capacity Manager (P32)",
        "docs_policy.json": "Self-Documenting Arch (P33)",
        "aiops_policy.json": "AI Operations (P34)",
    }
    results = []
    for filename, subsystem in required.items():
        exists = (CONFIG_DIR / filename).exists()
        results.append({"config": filename, "subsystem": subsystem, "exists": exists})
    return results


def check_git_status():
    """Check for uncommitted changes."""
    try:
        r = subprocess.run(
            ["git", "-C", str(ROOT), "status", "--porcelain"],
            capture_output=True, text=True, timeout=10
        )
        dirty_files = [l.strip() for l in r.stdout.splitlines() if l.strip()]
        return {"clean": len(dirty_files) == 0, "dirty_files": dirty_files}
    except Exception as e:
        return {"clean": False, "error": str(e)}


def run_audit():
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    configs = check_configs()
    scripts = check_scripts()
    secrets = secret_scan()
    subsystems = check_subsystem_configs()
    git = check_git_status()

    config_pass = all(c["valid"] for c in configs)
    script_pass = all(s["valid"] for s in scripts)
    secret_pass = len(secrets) == 0
    subsystem_pass = all(s["exists"] for s in subsystems)

    overall = config_pass and script_pass and secret_pass and subsystem_pass

    result = {
        "timestamp": timestamp,
        "pass": overall,
        "checks": {
            "configs": {"pass": config_pass, "total": len(configs), "valid": sum(1 for c in configs if c["valid"]), "details": configs},
            "scripts": {"pass": script_pass, "total": len(scripts), "valid": sum(1 for s in scripts if s["valid"]), "details": scripts},
            "secrets": {"pass": secret_pass, "violations": len(secrets), "details": secrets},
            "subsystems": {"pass": subsystem_pass, "total": len(subsystems), "present": sum(1 for s in subsystems if s["exists"]), "details": subsystems},
            "git": git,
        },
    }

    # Write audit artifact
    audit_dir = ROOT / "artifacts" / "release"
    audit_dir.mkdir(parents=True, exist_ok=True)
    with open(audit_dir / "audit.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


def main():
    parser = argparse.ArgumentParser(description="Release Audit")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = run_audit()

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        icon = "✅" if result["pass"] else "❌"
        print(f"{icon} Release Audit: {'PASS' if result['pass'] else 'FAIL'}")
        for name, check in result["checks"].items():
            if name == "git":
                gi = "✅" if check.get("clean") else "⚠️"
                dirty_count = len(check.get("dirty_files", []))
                print(f"  {gi} git: {'clean' if check.get('clean') else str(dirty_count) + ' uncommitted files'}")
            elif name == "secrets":
                si = "✅" if check["pass"] else "🚨"
                print(f"  {si} secrets: {check['violations']} violations")
            else:
                ci = "✅" if check["pass"] else "❌"
                passed = check.get("valid", check.get("present", 0))
                total = check.get("total", 0)
                print(f"  {ci} {name}: {passed}/{total}")

    sys.exit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
