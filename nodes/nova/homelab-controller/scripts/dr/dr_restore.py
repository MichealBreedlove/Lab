#!/usr/bin/env python3
"""D5 — DR Restore Engine: builds and optionally executes a restore plan."""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "artifacts" / "dr"
CONFIG_DIR = ROOT / "config"


def load_json(path):
    with open(path) as f:
        return json.load(f)


def check_break_glass(policy):
    """Verify break-glass token is present and fresh."""
    bg = policy.get("break_glass", {})
    token_path = ROOT / bg.get("token_path", "config/break_glass.token")
    if not token_path.exists():
        return False, "break-glass token not found"
    max_min = bg.get("max_minutes_valid", 30)
    age_min = (time.time() - token_path.stat().st_mtime) / 60
    if age_min > max_min:
        return False, f"break-glass token expired ({age_min:.0f}m > {max_min}m)"
    return True, "break-glass valid"


def check_cluster_green(policy):
    """Check if cluster is healthy (via SLO artifacts)."""
    if not policy.get("require_cluster_green", True):
        return True, "cluster check disabled"
    slo_path = ROOT / "artifacts" / "slo" / "current.json"
    if not slo_path.exists():
        return False, "no SLO data available"
    try:
        data = load_json(slo_path)
        exhausted = data.get("summary", {}).get("slos_exhausted", 0)
        if exhausted > 0:
            return False, f"{exhausted} SLOs have exhausted budgets"
        return True, "cluster green"
    except Exception as e:
        return False, f"SLO check error: {e}"


def build_restore_plan(node, targets, policy):
    """Build ordered list of restore actions for a node."""
    node_cfg = targets["nodes"].get(node)
    if not node_cfg:
        return {"error": f"node {node} not found in restore_targets.json"}

    plan = {
        "node": node,
        "platform": node_cfg["platform"],
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": policy.get("mode", "supervised"),
        "actions": [],
    }

    # Package installation
    if node_cfg.get("packages"):
        plan["actions"].append({
            "step": "install_packages",
            "type": "command",
            "destructive": False,
            "command": f"apt-get install -y {' '.join(node_cfg['packages'])}",
            "description": f"Install required packages: {', '.join(node_cfg['packages'])}",
        })

    # Component restores
    for unit_name in node_cfg.get("restore_units", []):
        comp = node_cfg["components"].get(unit_name, {})
        action = {
            "step": f"restore_{unit_name}",
            "type": comp.get("type", "files"),
            "destructive": comp.get("type") in ("systemd_user", "schtasks"),
            "component": unit_name,
            "source_paths": comp.get("source_paths", []),
            "dest_paths": comp.get("dest_paths", []),
            "description": comp.get("notes", f"Restore {unit_name}"),
        }
        plan["actions"].append(action)

        # Restart commands
        for cmd in comp.get("restart", []):
            plan["actions"].append({
                "step": f"restart_{unit_name}",
                "type": "command",
                "destructive": False,
                "command": cmd,
                "description": f"Restart after {unit_name} restore",
            })

    return plan


def execute_action(action, dry_run=True):
    """Execute a single restore action. Returns result dict."""
    result = {
        "step": action["step"],
        "type": action["type"],
        "dry_run": dry_run,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    if dry_run:
        result["status"] = "skipped_dry_run"
        result["description"] = action.get("description", "")
        return result

    if action["type"] == "command":
        try:
            r = subprocess.run(
                action["command"], shell=True, capture_output=True, text=True, timeout=60
            )
            result["status"] = "ok" if r.returncode == 0 else "failed"
            result["returncode"] = r.returncode
            result["stdout"] = r.stdout[:500]
            result["stderr"] = r.stderr[:500]
        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
    elif action["type"] == "files":
        # Copy files from repo to destination
        for src, dst in zip(action.get("source_paths", []), action.get("dest_paths", [])):
            src_full = ROOT.parents[2] / src  # Lab repo root
            dst_full = Path(os.path.expanduser(dst))
            try:
                if src_full.is_dir():
                    if dst_full.exists():
                        shutil.rmtree(dst_full)
                    shutil.copytree(src_full, dst_full)
                elif src_full.is_file():
                    dst_full.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_full, dst_full)
                result["status"] = "ok"
            except Exception as e:
                result["status"] = "error"
                result["error"] = str(e)
    else:
        result["status"] = "skipped_unknown_type"

    return result


def run_restore(node, mode="dry-run"):
    policy = load_json(CONFIG_DIR / "dr_policy.json")
    targets = load_json(CONFIG_DIR / "restore_targets.json")

    dry_run = mode == "dry-run"
    autonomous = mode == "autonomous"

    # Safety checks
    if autonomous and policy.get("mode") != "autonomous":
        return {"error": "autonomous mode not allowed by policy", "policy_mode": policy["mode"]}

    cluster_ok, cluster_msg = check_cluster_green(policy)
    if not cluster_ok and policy.get("require_cluster_green", True) and not dry_run:
        return {"error": f"cluster not green: {cluster_msg}", "skip_reason": cluster_msg}

    plan = build_restore_plan(node, targets, policy)
    if "error" in plan:
        return plan

    # Check break-glass for destructive actions
    has_destructive = any(a.get("destructive") for a in plan["actions"])
    if has_destructive and not dry_run and policy.get("break_glass", {}).get("required_for_destructive"):
        bg_ok, bg_msg = check_break_glass(policy)
        if not bg_ok:
            return {"error": f"break-glass required: {bg_msg}", "plan": plan}

    # Execute
    results = []
    for action in plan["actions"]:
        result = execute_action(action, dry_run=dry_run)
        results.append(result)

    plan["results"] = results
    plan["overall_status"] = "ok" if all(r.get("status") in ("ok", "skipped_dry_run") for r in results) else "failed"

    # Write artifacts
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(ARTIFACTS_DIR / "restore_plan.json", "w") as f:
        json.dump(plan, f, indent=2)

    # Append to run log
    with open(ARTIFACTS_DIR / "restore_run.jsonl", "a") as f:
        f.write(json.dumps({"timestamp": plan["timestamp"], "node": node, "mode": mode, "status": plan["overall_status"]}) + "\n")

    return plan


def main():
    parser = argparse.ArgumentParser(description="DR Restore Engine")
    parser.add_argument("--node", required=True, help="Target node name")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Generate plan only (default)")
    parser.add_argument("--apply", action="store_true", help="Execute restore (supervised)")
    parser.add_argument("--autonomous", action="store_true", help="Execute restore (autonomous, policy-gated)")
    parser.add_argument("--json", action="store_true", help="JSON output only")
    args = parser.parse_args()

    mode = "autonomous" if args.autonomous else "apply" if args.apply else "dry-run"
    result = run_restore(args.node, mode=mode)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if "error" in result:
            print(f"❌ Restore failed: {result['error']}")
        else:
            status = result.get("overall_status", "unknown")
            icon = "✅" if status == "ok" else "❌"
            print(f"{icon} Restore {'plan' if mode == 'dry-run' else 'execution'}: {status}")
            print(f"  Node: {result['node']} ({result['platform']})")
            print(f"  Mode: {mode}")
            print(f"  Actions: {len(result.get('actions', []))}")
            for r in result.get("results", []):
                s = r.get("status", "?")
                step_icon = "✅" if s in ("ok", "skipped_dry_run") else "❌"
                print(f"    {step_icon} {r['step']}: {s}")

    sys.exit(0 if result.get("overall_status") == "ok" or "error" not in result else 1)


if __name__ == "__main__":
    main()
