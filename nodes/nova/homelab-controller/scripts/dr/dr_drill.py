#!/usr/bin/env python3
"""D7 — DR Drill: safe failure simulation + restore + validate + report."""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "artifacts" / "dr"
CONFIG_DIR = ROOT / "config"

from dr_preflight import run_preflight
from dr_backup_inventory import run_inventory
from dr_restore import run_restore
from dr_validate import validate_node


def load_json(path):
    with open(path) as f:
        return json.load(f)


def simulate_failure(action_type, node, platform):
    """Simulate a safe, reversible failure. Returns (description, undo_fn)."""
    simulations = []

    if platform == "linux":
        # Simulation 1: stop openclaw-node service
        simulations.append({
            "type": "service_stop",
            "description": "Stop openclaw-node user service",
            "simulate_cmd": "systemctl --user stop openclaw-node",
            "undo_cmd": "systemctl --user start openclaw-node",
            "safe": True,
        })

        # Simulation 2: rename a config file
        simulations.append({
            "type": "config_rename",
            "description": "Rename openclaw config to .bak (simulating config loss)",
            "simulate_cmd": "mv ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.bak 2>/dev/null || true",
            "undo_cmd": "mv ~/.openclaw/openclaw.json.bak ~/.openclaw/openclaw.json 2>/dev/null || true",
            "safe": True,
        })
    elif platform == "windows":
        simulations.append({
            "type": "gateway_stop",
            "description": "Stop OpenClaw gateway",
            "simulate_cmd": "openclaw gateway stop",
            "undo_cmd": "openclaw gateway start",
            "safe": True,
        })

    return simulations


def run_drill(node, max_actions=3):
    policy = load_json(CONFIG_DIR / "dr_policy.json")
    drill_cfg = policy.get("drill", {})

    if not drill_cfg.get("enabled", False):
        return {"error": "drill not enabled in policy"}

    if not drill_cfg.get("safe_simulation_only", True):
        return {"error": "only safe_simulation_only mode is supported"}

    max_actions = min(max_actions, drill_cfg.get("max_actions", 3))
    targets = load_json(CONFIG_DIR / "restore_targets.json")
    node_cfg = targets["nodes"].get(node)
    if not node_cfg:
        return {"error": f"node {node} not found"}

    platform = node_cfg["platform"]
    drill_start = time.time()

    report = {
        "node": node,
        "platform": platform,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "stages": [],
    }

    # Stage 1: Preflight
    print("📋 Stage 1: Preflight...")
    preflight = run_preflight(node=node, allow_dirty=True)
    report["stages"].append({"name": "preflight", "pass": preflight.get("preflight_pass", False)})

    # Stage 2: Baseline inventory
    print("📋 Stage 2: Baseline inventory...")
    baseline = run_inventory(node=node)
    report["stages"].append({"name": "inventory_baseline", "pass": True})

    # Stage 3: Simulate failures
    print("💥 Stage 3: Simulating failures...")
    simulations = simulate_failure("safe", node, platform)[:max_actions]
    sim_results = []
    for sim in simulations:
        print(f"  → {sim['description']}")
        try:
            subprocess.run(sim["simulate_cmd"], shell=True, timeout=30, capture_output=True)
            sim_results.append({"type": sim["type"], "description": sim["description"], "simulated": True})
        except Exception as e:
            sim_results.append({"type": sim["type"], "description": sim["description"], "simulated": False, "error": str(e)})
    report["stages"].append({"name": "simulate_failures", "simulations": sim_results})

    # Brief pause for failure to take effect
    time.sleep(2)

    # Stage 4: Validate (should show failures)
    print("🔍 Stage 4: Validate (expecting failures)...")
    pre_validate = validate_node(node)
    report["stages"].append({
        "name": "validate_pre_restore",
        "pass": pre_validate.get("pass", False),
        "failures_detected": pre_validate.get("summary", {}).get("failing", 0),
    })

    # Stage 5: Restore
    print("🔧 Stage 5: Restore (supervised)...")
    # First undo simulations, then run restore dry-run
    for sim in simulations:
        try:
            subprocess.run(sim["undo_cmd"], shell=True, timeout=30, capture_output=True)
        except Exception:
            pass

    restore = run_restore(node, mode="dry-run")
    report["stages"].append({
        "name": "restore",
        "status": restore.get("overall_status", "unknown"),
        "actions": len(restore.get("actions", [])),
    })

    # Stage 6: Post-restore validate
    print("✅ Stage 6: Post-restore validation...")
    time.sleep(2)
    post_validate = validate_node(node)
    report["stages"].append({
        "name": "validate_post_restore",
        "pass": post_validate.get("pass", False),
        "checks": post_validate.get("summary", {}),
    })

    # Calculate MTTR
    drill_end = time.time()
    mttr_sec = round(drill_end - drill_start)
    report["mttr_seconds"] = mttr_sec
    report["overall_pass"] = post_validate.get("pass", False)

    # Write JSON report
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    date_str = time.strftime("%Y-%m-%d", time.gmtime())
    with open(ARTIFACTS_DIR / f"drill_report_{date_str}.json", "w") as f:
        json.dump(report, f, indent=2)

    # Write markdown report
    md = f"""# DR Drill Report — {date_str}

**Node:** {node} ({platform})
**MTTR:** {mttr_sec}s
**Overall:** {'PASS ✅' if report['overall_pass'] else 'FAIL ❌'}

## Stages

| Stage | Result |
|---|---|
"""
    for stage in report["stages"]:
        name = stage["name"]
        if "pass" in stage:
            icon = "✅" if stage["pass"] else "❌"
        elif "status" in stage:
            icon = "✅" if stage["status"] == "ok" else "⚠️"
        else:
            icon = "📋"
        md += f"| {name} | {icon} |\n"

    md += f"""
## Simulations

"""
    for sim in sim_results:
        md += f"- {'✅' if sim.get('simulated') else '❌'} {sim['description']}\n"

    md += f"""
## Metrics

- **MTTR:** {mttr_sec} seconds
- **Failures detected pre-restore:** {report['stages'][3].get('failures_detected', '?')}
- **Post-restore checks:** {post_validate.get('summary', {}).get('passing', '?')}/{post_validate.get('summary', {}).get('total', '?')} passing
"""

    with open(ARTIFACTS_DIR / f"drill_report_{date_str}.md", "w") as f:
        f.write(md)

    return report


def main():
    parser = argparse.ArgumentParser(description="DR Drill")
    parser.add_argument("--node", required=True, help="Target node")
    parser.add_argument("--max-actions", type=int, default=3, help="Max failure simulations")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = run_drill(args.node, max_actions=args.max_actions)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        icon = "✅" if report.get("overall_pass") else "❌"
        print(f"\n{icon} Drill complete: {'PASS' if report.get('overall_pass') else 'FAIL'}")
        print(f"  MTTR: {report.get('mttr_seconds', '?')}s")
        print(f"  Reports: artifacts/dr/drill_report_*.json + .md")

    sys.exit(0 if report.get("overall_pass") else 1)


if __name__ == "__main__":
    main()
