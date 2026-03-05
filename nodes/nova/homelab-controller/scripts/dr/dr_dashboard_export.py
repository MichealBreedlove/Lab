#!/usr/bin/env python3
"""DR Dashboard Export: merges DR artifacts into a single dr_status.json for the dashboard."""

import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "artifacts" / "dr"
CONFIG_DIR = ROOT / "config"
DASHBOARD_DATA = ROOT / "dashboard" / "static" / "data"


def load_json_safe(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def compute_readiness(preflight, validates, drill, policy):
    """Compute readiness score 0-100."""
    score = 0
    thresholds = policy.get("scoring", {})

    # Preflight pass: 25 points
    if preflight and preflight.get("preflight_pass"):
        score += 25

    # Validate pass across nodes: 35 points
    if validates:
        total_checks = sum(v.get("summary", {}).get("total", 0) for v in validates.values())
        passing_checks = sum(v.get("summary", {}).get("passing", 0) for v in validates.values())
        if total_checks > 0:
            score += int(35 * (passing_checks / total_checks))

    # Drill recent + pass: 25 points
    if drill:
        if drill.get("overall_pass"):
            score += 25
        elif drill.get("timestamp"):
            score += 10  # Partial credit for having run a drill

    # Policy enabled: 15 points
    if policy.get("enabled"):
        score += 10
        if policy.get("drill", {}).get("enabled"):
            score += 5

    green_min = thresholds.get("readiness_green_min", 85)
    yellow_min = thresholds.get("readiness_yellow_min", 70)

    if score >= green_min:
        status = "GREEN"
    elif score >= yellow_min:
        status = "YELLOW"
    else:
        status = "RED"

    return score, status


def export():
    policy = load_json_safe(CONFIG_DIR / "dr_policy.json") or {}
    targets = load_json_safe(CONFIG_DIR / "restore_targets.json") or {}
    preflight = load_json_safe(ARTIFACTS_DIR / "preflight.json")

    # Load per-node validates and inventories
    validates = {}
    nodes_status = {}
    for node_name, node_cfg in targets.get("nodes", {}).items():
        validate = load_json_safe(ARTIFACTS_DIR / f"validate_{node_name}.json")
        inventory = load_json_safe(ARTIFACTS_DIR / f"inventory_{node_name}.json")
        validates[node_name] = validate or {}

        nodes_status[node_name] = {
            "platform": node_cfg.get("platform", "unknown"),
            "components": len(node_cfg.get("restore_units", [])),
            "validate_pass": validate.get("pass", False) if validate else False,
            "checks_passing": validate.get("summary", {}).get("passing", 0) if validate else 0,
            "checks_total": validate.get("summary", {}).get("total", 0) if validate else 0,
            "inventory_ts": inventory.get("timestamp", "") if inventory else "",
        }

    # Find latest drill report
    drill = None
    drill_files = sorted(ARTIFACTS_DIR.glob("drill_report_*.json"), reverse=True)
    if drill_files:
        drill = load_json_safe(drill_files[0])

    # Break-glass state
    bg_path = ROOT / policy.get("break_glass", {}).get("token_path", "config/break_glass.token")
    if bg_path.exists():
        age_min = (time.time() - bg_path.stat().st_mtime) / 60
        max_min = policy.get("break_glass", {}).get("max_minutes_valid", 30)
        bg_state = "active" if age_min <= max_min else "expired"
    else:
        bg_state = "none"

    # Compute readiness
    score, status = compute_readiness(preflight, validates, drill, policy)

    # Build export
    dr_status = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "readiness_score": score,
        "status": status,
        "break_glass_state": bg_state,
        "last_drill_mttr_sec": drill.get("mttr_seconds") if drill else None,
        "last_drill_ts": drill.get("timestamp") if drill else None,
        "preflight": {
            "pass": preflight.get("preflight_pass", False) if preflight else False,
            "node": preflight.get("node", "") if preflight else "",
            "platform": preflight.get("platform", "") if preflight else "",
            "git_ok": preflight.get("git", {}).get("remote_ok", False) and preflight.get("git", {}).get("branch_ok", False) if preflight else False,
            "binaries_ok": all(preflight.get("binaries", {}).values()) if preflight else False,
            "snapshot_fresh": preflight.get("snapshot", {}).get("fresh", False) if preflight else False,
            "timestamp": preflight.get("timestamp", "") if preflight else "",
        },
        "last_drill": {
            "timestamp": drill.get("timestamp", "") if drill else "",
            "pass": drill.get("overall_pass", False) if drill else False,
            "mttr_sec": drill.get("mttr_seconds") if drill else None,
            "stages_pass": sum(1 for s in drill.get("stages", []) if s.get("pass", s.get("status") == "ok")) if drill else 0,
            "stages_total": len(drill.get("stages", [])) if drill else 0,
        } if drill else {},
        "nodes": nodes_status,
    }

    # Write to dashboard data directory
    DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)
    with open(DASHBOARD_DATA / "dr_status.json", "w") as f:
        json.dump(dr_status, f, indent=2)

    # Also write to artifacts
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(ARTIFACTS_DIR / "dr_status.json", "w") as f:
        json.dump(dr_status, f, indent=2)

    return dr_status


if __name__ == "__main__":
    result = export()
    print(f"{'🟢' if result['status'] == 'GREEN' else '🟡' if result['status'] == 'YELLOW' else '🔴'} DR Readiness: {result['status']} (score: {result['readiness_score']})")
    print(f"  Written: dashboard/static/data/dr_status.json")
