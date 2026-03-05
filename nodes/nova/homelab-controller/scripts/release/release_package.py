#!/usr/bin/env python3
"""P35 — Release Package: create release manifest and verify completeness."""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASE_DIR = ROOT / "release" / "v1.0"
ARTIFACTS_DIR = ROOT / "artifacts" / "release"


def get_git_info():
    info = {}
    try:
        r = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10)
        info["commit"] = r.stdout.strip()[:8]
    except Exception:
        info["commit"] = "unknown"
    try:
        r = subprocess.run(["git", "-C", str(ROOT), "rev-list", "--count", "HEAD"], capture_output=True, text=True, timeout=10)
        info["total_commits"] = int(r.stdout.strip())
    except Exception:
        info["total_commits"] = 0
    try:
        r = subprocess.run(["git", "-C", str(ROOT), "log", "--format=%s", "--max-count=1"], capture_output=True, text=True, timeout=10)
        info["last_message"] = r.stdout.strip()
    except Exception:
        info["last_message"] = ""
    return info


def count_files():
    """Count project files by type."""
    counts = {}
    for f in ROOT.rglob("*"):
        if f.is_dir() or ".git" in str(f) or "__pycache__" in str(f):
            continue
        ext = f.suffix or "other"
        counts[ext] = counts.get(ext, 0) + 1
    return counts


def count_lines():
    """Count lines of code."""
    total = 0
    for ext in [".py", ".sh", ".ps1"]:
        for f in ROOT.rglob(f"*{ext}"):
            if ".git" in str(f) or "__pycache__" in str(f):
                continue
            try:
                total += len(f.read_text().splitlines())
            except Exception:
                pass
    return total


def verify_release_docs():
    required = [
        RELEASE_DIR / "RELEASE_NOTES.md",
        RELEASE_DIR / "RESTORE_GUIDE.md",
        RELEASE_DIR / "SYSTEM_ARCHITECTURE.md",
    ]
    return [{"file": str(f.relative_to(ROOT)), "exists": f.exists()} for f in required]


def build_manifest():
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    git = get_git_info()
    files = count_files()
    loc = count_lines()
    docs = verify_release_docs()

    # Subsystem inventory
    subsystems = [
        {"name": "Disaster Recovery", "priority": "P30", "config": "config/dr_policy.json", "scripts": "scripts/dr/"},
        {"name": "Node Bootstrap", "priority": "P31", "config": "config/bootstrap_policy.json", "scripts": "scripts/bootstrap/"},
        {"name": "Capacity Manager", "priority": "P32", "config": "config/capacity_policy.json", "scripts": "scripts/capacity/"},
        {"name": "Self-Documenting Arch", "priority": "P33", "config": "config/docs_policy.json", "scripts": "scripts/docs/"},
        {"name": "AI Operations", "priority": "P34", "config": "config/aiops_policy.json", "scripts": "scripts/aiops/"},
        {"name": "Release", "priority": "P35", "scripts": "scripts/release/"},
    ]

    for sub in subsystems:
        cfg_path = ROOT / sub.get("config", "")
        sub["config_exists"] = cfg_path.exists() if sub.get("config") else True
        scripts_path = ROOT / sub["scripts"]
        sub["scripts_exist"] = scripts_path.exists()

    manifest = {
        "version": "1.0.0",
        "timestamp": timestamp,
        "git": git,
        "statistics": {
            "files_by_type": files,
            "lines_of_code": loc,
            "total_files": sum(files.values()),
        },
        "subsystems": subsystems,
        "release_docs": docs,
        "all_docs_present": all(d["exists"] for d in docs),
        "all_subsystems_present": all(s["config_exists"] and s["scripts_exist"] for s in subsystems),
    }

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(ARTIFACTS_DIR / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    with open(RELEASE_DIR / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    return manifest


def main():
    parser = argparse.ArgumentParser(description="Release Package")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    manifest = build_manifest()

    if args.json:
        print(json.dumps(manifest, indent=2))
    else:
        print(f"📦 Release Package: v{manifest['version']}")
        print(f"  Commit: {manifest['git']['commit']} ({manifest['git']['total_commits']} total)")
        print(f"  Files: {manifest['statistics']['total_files']} | LoC: {manifest['statistics']['lines_of_code']}")
        print(f"  Subsystems: {len(manifest['subsystems'])}")
        print(f"  Docs: {'✅ all present' if manifest['all_docs_present'] else '❌ missing docs'}")
        print(f"  Subsystems: {'✅ all present' if manifest['all_subsystems_present'] else '❌ missing subsystems'}")

    sys.exit(0)


if __name__ == "__main__":
    main()
