#!/usr/bin/env python3
"""P31 — Bootstrap Configure: set up OpenClaw node config, timers, and node-specific settings."""

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


def ssh_cmd(host, user, key_path, command, timeout=60):
    key_path = str(Path(key_path).expanduser())
    try:
        r = subprocess.run(
            ["ssh", "-o", "StrictHostKeyChecking=accept-new",
             "-o", "ConnectTimeout=10",
             "-i", key_path,
             f"{user}@{host}", command],
            capture_output=True, text=True, timeout=timeout
        )
        return {"ok": r.returncode == 0, "stdout": r.stdout.strip()[:500], "stderr": r.stderr.strip()[:500]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def run_configure(node_name, dry_run=True):
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
    gateway_host = policy.get("openclaw", {}).get("gateway_host", "10.1.1.150")
    gateway_port = policy.get("openclaw", {}).get("gateway_port", 18789)
    clone_target = policy.get("git", {}).get("clone_target", "~/Lab")
    timers_cfg = policy.get("timers", {})

    steps = []

    # Step 1: Create .openclaw directory
    steps.append({
        "name": "create_openclaw_dir",
        "command": "mkdir -p ~/.openclaw",
        "description": "Create OpenClaw config directory",
    })

    # Step 2: Configure OpenClaw node to point at gateway
    steps.append({
        "name": "configure_openclaw",
        "command": f'openclaw node pair --gateway ws://{gateway_host}:{gateway_port} --name {node_name} || echo "Manual pairing may be needed"',
        "description": f"Pair node with gateway at {gateway_host}:{gateway_port}",
    })

    # Step 3: Copy node-specific configs from repo
    steps.append({
        "name": "copy_node_configs",
        "command": f"cp -r {clone_target}/nodes/{node_name}/openclaw/* ~/.openclaw/ 2>/dev/null || echo 'No existing configs to copy'",
        "description": "Copy node-specific OpenClaw configs from repo",
    })

    # Step 4: Enable OpenClaw node service
    steps.append({
        "name": "enable_openclaw_service",
        "command": "systemctl --user enable openclaw-node 2>/dev/null; systemctl --user start openclaw-node 2>/dev/null || openclaw node start",
        "description": "Enable and start OpenClaw node service",
    })

    # Step 5: Install backup timer
    if timers_cfg.get("enable_backup", True):
        steps.append({
            "name": "install_backup_timer",
            "command": f"cd {clone_target} && bash tools/backup/linux/install_timer.sh 2>/dev/null || echo 'Timer install script not found'",
            "description": "Install systemd backup timer",
        })

    # Step 6: Set up homelab-controller (controller profile only)
    if profile.get("install_homelab_controller", False):
        steps.append({
            "name": "setup_homelab_controller",
            "command": f"ln -sf {clone_target}/nodes/{node_name}/homelab-controller ~/homelab-controller 2>/dev/null; chmod +x ~/homelab-controller/bin/oc.sh 2>/dev/null || true",
            "description": "Link homelab-controller and make CLI executable",
        })

    # Step 7: Create node directory in repo if missing
    steps.append({
        "name": "init_node_repo_dir",
        "command": f"mkdir -p {clone_target}/nodes/{node_name}/openclaw {clone_target}/nodes/{node_name}/logs",
        "description": "Initialize node directory structure in Lab repo",
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
    with open(ARTIFACTS_DIR / f"configure_{node_name}.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


def main():
    parser = argparse.ArgumentParser(description="Bootstrap Configure")
    parser.add_argument("--node", required=True)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    dry_run = not args.apply
    result = run_configure(args.node, dry_run=dry_run)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        icon = "✅" if result.get("overall_status") == "ok" else "❌"
        mode = "DRY RUN" if dry_run else "APPLY"
        print(f"{icon} Bootstrap configure ({mode}): {result.get('overall_status')}")
        for s in result.get("steps", []):
            si = "✅" if s["status"] in ("ok", "skipped_dry_run") else "❌"
            print(f"  {si} {s['name']}: {s['description']}")

    sys.exit(0 if result.get("overall_status") == "ok" else 1)


if __name__ == "__main__":
    main()
