#!/usr/bin/env python3
"""D3 — DR Preflight checks: node identity, git state, binary availability, snapshot freshness."""

import argparse
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "artifacts" / "dr"
CONFIG_DIR = ROOT / "config"


def detect_node():
    hostname = socket.gethostname().lower()
    node_map = {"jasper": "jasper", "nova": "nova", "mira": "mira", "orin": "orin"}
    for key, name in node_map.items():
        if key in hostname:
            return name
    return hostname


def load_json(path):
    with open(path) as f:
        return json.load(f)


def check_git(repo_dir, allow_dirty=False):
    checks = {"remote_ok": False, "branch_ok": False, "clean": False}
    try:
        remote = subprocess.check_output(
            ["git", "remote", "get-url", "origin"], cwd=repo_dir, text=True
        ).strip()
        checks["remote_ok"] = "MichealBreedlove/Lab" in remote
        checks["remote"] = remote

        branch = subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=repo_dir, text=True
        ).strip()
        checks["branch_ok"] = branch == "main"
        checks["branch"] = branch

        status = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=repo_dir, text=True
        ).strip()
        checks["clean"] = len(status) == 0 or allow_dirty
        checks["dirty_files"] = len(status.splitlines()) if status else 0
    except Exception as e:
        checks["error"] = str(e)
    return checks


def check_binaries(plat):
    required = {
        "linux": ["git", "python3", "systemctl"],
        "windows": ["git", "pwsh"],
    }
    bins = required.get(plat, required["linux"])
    results = {}
    for b in bins:
        results[b] = shutil.which(b) is not None
    return results


def check_snapshot_freshness(policy):
    max_age = policy.get("require_snapshot_fresh_minutes", 30)
    snap_path = ROOT / "artifacts" / "snapshots" / "latest.json"
    if not snap_path.exists():
        # Try alternate locations
        for alt in [ROOT / "artifacts" / "slo" / "current.json"]:
            if alt.exists():
                snap_path = alt
                break
    if not snap_path.exists():
        return {"fresh": False, "reason": "no snapshot found", "max_age_min": max_age}

    age_sec = time.time() - snap_path.stat().st_mtime
    age_min = age_sec / 60
    return {
        "fresh": age_min <= max_age,
        "age_minutes": round(age_min, 1),
        "max_age_min": max_age,
        "path": str(snap_path),
    }


def run_preflight(node=None, repo_dir=None, allow_dirty=False):
    if node is None:
        node = detect_node()
    if repo_dir is None:
        # Walk up to find Lab repo root
        repo_dir = ROOT.parents[2]  # nodes/nova/homelab-controller -> Lab root
        if not (repo_dir / ".git").exists():
            repo_dir = ROOT

    policy = load_json(CONFIG_DIR / "dr_policy.json")
    targets = load_json(CONFIG_DIR / "restore_targets.json")

    node_config = targets.get("nodes", {}).get(node)
    plat = "windows" if platform.system() == "Windows" else "linux"

    result = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "node": node,
        "platform": plat,
        "hostname": socket.gethostname(),
        "policy_enabled": policy.get("enabled", False),
        "policy_mode": policy.get("mode", "supervised"),
        "node_known": node_config is not None,
        "git": check_git(str(repo_dir), allow_dirty),
        "binaries": check_binaries(plat),
        "snapshot": check_snapshot_freshness(policy),
    }

    # Compute pass/fail
    checks_pass = all(
        [
            result["policy_enabled"],
            result["node_known"],
            result["git"].get("remote_ok", False),
            result["git"].get("branch_ok", False),
            result["git"].get("clean", False),
            all(result["binaries"].values()),
        ]
    )
    result["preflight_pass"] = checks_pass

    # Write artifact
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = ARTIFACTS_DIR / "preflight.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)

    return result


def main():
    parser = argparse.ArgumentParser(description="DR Preflight Checks")
    parser.add_argument("--node", help="Node name (auto-detect if omitted)")
    parser.add_argument("--repo-dir", help="Path to Lab repo root")
    parser.add_argument("--allow-dirty", action="store_true", help="Allow uncommitted changes")
    parser.add_argument("--json", action="store_true", help="JSON output only")
    args = parser.parse_args()

    result = run_preflight(
        node=args.node,
        repo_dir=Path(args.repo_dir) if args.repo_dir else None,
        allow_dirty=args.allow_dirty,
    )

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        icon = "✅" if result["preflight_pass"] else "❌"
        print(f"{icon} Preflight: {'PASS' if result['preflight_pass'] else 'FAIL'}")
        print(f"  Node: {result['node']} ({result['platform']})")
        print(f"  Policy: {'enabled' if result['policy_enabled'] else 'DISABLED'} ({result['policy_mode']})")
        print(f"  Git: remote={'✅' if result['git'].get('remote_ok') else '❌'} "
              f"branch={'✅' if result['git'].get('branch_ok') else '❌'} "
              f"clean={'✅' if result['git'].get('clean') else '❌'}")
        bins = result["binaries"]
        missing = [k for k, v in bins.items() if not v]
        print(f"  Binaries: {'✅ all found' if not missing else '❌ missing: ' + ', '.join(missing)}")
        snap = result["snapshot"]
        print(f"  Snapshot: {'✅ fresh' if snap.get('fresh') else '⚠️ stale/missing'}"
              f" ({snap.get('age_minutes', '?')}m / {snap.get('max_age_min')}m max)")
        print(json.dumps(result, indent=2))

    sys.exit(0 if result["preflight_pass"] else 1)


if __name__ == "__main__":
    main()
