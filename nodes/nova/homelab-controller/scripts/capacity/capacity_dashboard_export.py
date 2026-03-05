#!/usr/bin/env python3
"""P32 — Capacity Dashboard Export: merge capacity data into dashboard-ready JSON."""

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "artifacts" / "capacity"
DASHBOARD_DATA = ROOT / "dashboard" / "static" / "data"


def load_json_safe(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def export():
    latest = load_json_safe(ARTIFACTS_DIR / "latest.json")
    forecast = load_json_safe(ARTIFACTS_DIR / "forecast.json")
    recommendations = load_json_safe(ARTIFACTS_DIR / "recommendations.json")

    if not latest:
        return None

    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    nodes = {}

    for name, data in latest.get("nodes", {}).items():
        if data.get("status") == "skipped":
            nodes[name] = {"status": "skipped", "platform": "windows"}
            continue

        node_data = {
            "cpu_pct": data.get("cpu_pct"),
            "memory_pct": data.get("memory_pct"),
            "disk_pct": data.get("disk_pct"),
            "load_ratio": data.get("load_ratio"),
            "cpu_cores": data.get("cpu_cores"),
            "memory_total_gb": data.get("memory_total_gb"),
            "disk_total_gb": data.get("disk_total_gb"),
            "alerts": len(data.get("alerts", [])),
            "status": "ok" if not data.get("alerts") else "warning" if all(a["level"] == "warning" for a in data.get("alerts", [])) else "critical",
        }

        # Add forecast if available
        if forecast:
            fc = forecast.get("forecasts", {}).get(name, {})
            node_data["forecast_disk_days"] = fc.get("disk", {}).get("days_until_full")
            node_data["forecast_mem_days"] = fc.get("mem", {}).get("days_until_full")

        nodes[name] = node_data

    # Overall status
    statuses = [n.get("status", "ok") for n in nodes.values() if n.get("status") != "skipped"]
    if any(s == "critical" for s in statuses):
        overall = "RED"
    elif any(s == "warning" for s in statuses):
        overall = "YELLOW"
    else:
        overall = "GREEN"

    dashboard_data = {
        "timestamp": timestamp,
        "collection_ts": latest.get("timestamp"),
        "status": overall,
        "nodes": nodes,
        "alert_count": len(latest.get("alerts", [])),
        "recommendation_count": recommendations.get("summary", {}).get("total", 0) if recommendations else 0,
    }

    DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)
    with open(DASHBOARD_DATA / "capacity_status.json", "w") as f:
        json.dump(dashboard_data, f, indent=2)

    return dashboard_data


if __name__ == "__main__":
    result = export()
    if result:
        icon = "🟢" if result["status"] == "GREEN" else "🟡" if result["status"] == "YELLOW" else "🔴"
        print(f"{icon} Capacity: {result['status']} ({result['alert_count']} alerts, {result['recommendation_count']} recommendations)")
        print(f"  Written: dashboard/static/data/capacity_status.json")
    else:
        print("⏭️  No capacity data to export")
