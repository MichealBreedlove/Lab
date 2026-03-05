#!/usr/bin/env python3
"""P32 — Capacity Recommender: generate actionable recommendations from metrics + forecasts."""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "artifacts" / "capacity"
CONFIG_DIR = ROOT / "config"


def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def generate_recommendations():
    policy = load_json(CONFIG_DIR / "capacity_policy.json") or {}
    latest = load_json(ARTIFACTS_DIR / "latest.json")
    forecast = load_json(ARTIFACTS_DIR / "forecast.json")

    recommendations = []
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    if not latest:
        return {"timestamp": timestamp, "recommendations": [{"action": "collect", "reason": "No capacity data. Run oc capacity collect first.", "priority": "high"}]}

    nodes = latest.get("nodes", {})
    thresholds = policy.get("thresholds", {})

    # Check for high CPU nodes
    high_cpu_nodes = [
        (n, d) for n, d in nodes.items()
        if d.get("status") == "ok" and d.get("cpu_pct", 0) >= thresholds.get("cpu_warn_pct", 80)
    ]
    if high_cpu_nodes:
        for name, data in high_cpu_nodes:
            recommendations.append({
                "action": "investigate_cpu",
                "node": name,
                "reason": f"CPU at {data['cpu_pct']}% (threshold: {thresholds.get('cpu_warn_pct', 80)}%)",
                "suggestion": f"Check running processes on {name}: ssh micheal@{data.get('ip', '?')} 'ps aux --sort=-%cpu | head -10'",
                "priority": "high" if data["cpu_pct"] >= thresholds.get("cpu_crit_pct", 95) else "medium",
            })

    # Check for high memory nodes
    high_mem_nodes = [
        (n, d) for n, d in nodes.items()
        if d.get("status") == "ok" and d.get("memory_pct", 0) >= thresholds.get("memory_warn_pct", 80)
    ]
    if high_mem_nodes:
        for name, data in high_mem_nodes:
            recommendations.append({
                "action": "investigate_memory",
                "node": name,
                "reason": f"Memory at {data['memory_pct']}% ({data.get('memory_avail_gb', '?')}GB free)",
                "suggestion": f"Check memory consumers: ssh micheal@{data.get('ip', '?')} 'ps aux --sort=-%mem | head -10'",
                "priority": "high" if data["memory_pct"] >= thresholds.get("memory_crit_pct", 95) else "medium",
            })

    # Check for disk pressure
    high_disk_nodes = [
        (n, d) for n, d in nodes.items()
        if d.get("status") == "ok" and d.get("disk_pct", 0) >= thresholds.get("disk_warn_pct", 80)
    ]
    if high_disk_nodes:
        for name, data in high_disk_nodes:
            recommendations.append({
                "action": "cleanup_disk",
                "node": name,
                "reason": f"Disk at {data['disk_pct']}% ({data.get('disk_avail_gb', '?')}GB free)",
                "suggestion": f"Clean up: ssh micheal@{data.get('ip', '?')} 'sudo apt autoremove -y; sudo journalctl --vacuum-time=7d'",
                "priority": "high" if data["disk_pct"] >= thresholds.get("disk_crit_pct", 90) else "medium",
            })

    # Check for load imbalance (rebalance recommendation)
    ok_nodes = {n: d for n, d in nodes.items() if d.get("status") == "ok" and d.get("load_ratio") is not None}
    if len(ok_nodes) >= 2:
        loads = {n: d["load_ratio"] for n, d in ok_nodes.items()}
        max_node = max(loads, key=loads.get)
        min_node = min(loads, key=loads.get)
        if loads[max_node] > 2 * loads[min_node] and loads[max_node] >= thresholds.get("load_warn_ratio", 2.0):
            recommendations.append({
                "action": "rebalance",
                "reason": f"Load imbalance: {max_node}={loads[max_node]}x vs {min_node}={loads[min_node]}x",
                "suggestion": f"Consider moving workloads from {max_node} to {min_node}",
                "priority": "low",
            })

    # Forecast-based recommendations
    if forecast:
        for alert in forecast.get("alerts", []):
            recommendations.append({
                "action": "plan_capacity",
                "node": alert["node"],
                "reason": f"{alert['metric']} forecast: {alert['days_until_full']}d until full",
                "suggestion": f"Plan {'disk expansion' if alert['metric'] == 'disk' else 'memory upgrade'} for {alert['node']} within {alert['days_until_full']} days",
                "priority": alert["level"],
            })

    # If everything is fine
    if not recommendations:
        recommendations.append({
            "action": "none",
            "reason": "All nodes within thresholds, no capacity concerns",
            "priority": "info",
        })

    result = {
        "timestamp": timestamp,
        "recommendations": recommendations,
        "summary": {
            "total": len(recommendations),
            "high": sum(1 for r in recommendations if r["priority"] == "high"),
            "medium": sum(1 for r in recommendations if r["priority"] == "medium"),
            "low": sum(1 for r in recommendations if r["priority"] in ("low", "info")),
        },
    }

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(ARTIFACTS_DIR / "recommendations.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


def main():
    parser = argparse.ArgumentParser(description="Capacity Recommender")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = generate_recommendations()

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        s = result["summary"]
        print(f"💡 Capacity Recommendations: {s['total']} ({s['high']} high, {s['medium']} medium, {s['low']} low)")
        for r in result["recommendations"]:
            icon = "🚨" if r["priority"] == "high" else "⚠️" if r["priority"] == "medium" else "💡" if r["priority"] == "low" else "ℹ️"
            print(f"  {icon} [{r['priority']}] {r['action']}: {r['reason']}")
            if r.get("suggestion"):
                print(f"      → {r['suggestion']}")

    sys.exit(0)


if __name__ == "__main__":
    main()
