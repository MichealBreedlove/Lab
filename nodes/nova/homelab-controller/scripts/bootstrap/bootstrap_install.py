#!/usr/bin/env python3
"""P31 — Bootstrap Install: install packages, clone repo, set up deps on target node via SSH."""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "artifacts" / "bootstrap"
CONFIG_DIR = ROOT / "config"


def load_json(path):
    with open(path) as f:
        return json.load(f)


def ssh_cmd(host, user, key_path, command, timeout=120):
    """Execute a command on remote node via SSH."""
    key_path = str(Path(key_path).expanduser())
    try:
        r = subprocess.run(
            ["ssh", "-o", "StrictHostKeyChecking=accept-new",
             "-o", "ConnectTimeout=10",
             "-i", key_path,
             f"{user}@{host}", command],
            capture_output=True, text=True, timeout=timeout
        )
        return {
            "ok": r.returncode == 0,
            "returncode": r.returncode,
            "stdout": r.stdout.strip()[:1000],
            "stderr": r.stderr.strip()[:500],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def run_install(node_name, dry_run=True):
    policy = load_json(CONFIG_DIR / "bootstrap_policy.json")
    profiles = load_json(CONFIG_DIR / "node_profiles.json")

    node_cfg = profiles["nodes"].get(node_name)
    if not node_cfg:
        return {"error": f"node '{node_name}' not found"}

    profile_name = node_cfg.get("profile", "worker")
    profile = profiles["profiles"].get(profile_name, {})
    ip = node_cfg["ip"]
    user = policy.get("ssh_user", "micheal")
    key = policy.get("ssh_key_path", "~/.ssh/id_ed25519")
    clone_target = policy.get("git", {}).get("clone_target", "~/Lab")
    repo = policy.get("git", {}).get("repo", "MichealBreedlove/Lab")

    steps = []

    # Step 1: System update
    steps.append({
        "name": "apt_update",
        "command": "sudo apt-get update -qq",
        "description": "Update package index",
    })

    # Step 2: Install packages
    packages = profile.get("packages", [])
    if packages:
        steps.append({
            "name": "install_packages",
            "command": f"sudo apt-get install -y -qq {' '.join(packages)}",
            "description": f"Install: {', '.join(packages)}",
        })

    # Step 3: Install pip packages
    pip_packages = profile.get("pip_packages", [])
    if pip_packages:
        steps.append({
            "name": "install_pip",
            "command": f"pip3 install --user {' '.join(pip_packages)}",
            "description": f"Pip install: {', '.join(pip_packages)}",
        })

    # Step 4: Clone Lab repo
    steps.append({
        "name": "clone_repo",
        "command": f"if [ -d {clone_target}/.git ]; then cd {clone_target} && git pull --ff-only; else git clone https://github.com/{repo}.git {clone_target}; fi",
        "description": f"Clone/pull Lab repo to {clone_target}",
    })

    # Step 5: Install OpenClaw
    steps.append({
        "name": "install_openclaw",
        "command": "which openclaw || (curl -fsSL https://get.openclaw.ai | bash)",
        "description": "Install OpenClaw if not present",
    })

    # Step 6: Enable linger for systemd user services
    steps.append({
        "name": "enable_linger",
        "command": f"sudo loginctl enable-linger {user}",
        "description": "Enable systemd linger for user services",
    })

    result = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "node": node_name,
        "ip": ip,
        "profile": profile_name,
        "dry_run": dry_run,
        "steps": [],
    }

    for step in steps:
        if dry_run:
            result["steps"].append({
                "name": step["name"],
                "description": step["description"],
                "command": step["command"],
                "status": "skipped_dry_run",
            })
        else:
            r = ssh_cmd(ip, user, key, step["command"])
            result["steps"].append({
                "name": step["name"],
                "description": step["description"],
                "status": "ok" if r["ok"] else "failed",
                "detail": r,
            })

    result["overall_status"] = "ok" if all(
        s["status"] in ("ok", "skipped_dry_run") for s in result["steps"]
    ) else "failed"

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(ARTIFACTS_DIR / f"install_{node_name}.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


def main():
    parser = argparse.ArgumentParser(description="Bootstrap Install")
    parser.add_argument("--node", required=True)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    dry_run = not args.apply
    result = run_install(args.node, dry_run=dry_run)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        icon = "✅" if result.get("overall_status") == "ok" else "❌"
        mode = "DRY RUN" if dry_run else "APPLY"
        print(f"{icon} Bootstrap install ({mode}): {result.get('overall_status')}")
        print(f"  Node: {result['node']} ({result['ip']}) — profile: {result['profile']}")
        for s in result.get("steps", []):
            si = "✅" if s["status"] in ("ok", "skipped_dry_run") else "❌"
            print(f"  {si} {s['name']}: {s['status']} — {s['description']}")

    sys.exit(0 if result.get("overall_status") == "ok" else 1)


if __name__ == "__main__":
    main()
