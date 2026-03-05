#!/usr/bin/env python3
"""P34 — AIOps Incident Correlation: correlate alerts across time windows and nodes."""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "artifacts" / "aiops"
CAPACITY_DIR = ROOT / "artifacts" / "capacity"
DR_DIR = ROOT / "artifacts" / "dr"
CONFIG_DIR = ROOT / "config"


def load_json_safe(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def collect_events():
    """Gather all alert events from various subsystems."""
    events = []

    # Capacity alerts
    capacity = load_json_safe(CAPACITY_DIR / "latest.json")
    if capacity:
        for alert in capacity.get("alerts", []):
            events.append({
                "source": "capacity",
                "node": alert.get("node"),
                "metric": alert.get("metric"),
                "level": alert.get("level"),
                "value": alert.get("value"),
                "timestamp": capacity.get("timestamp", ""),
            })

    # Anomaly alerts
    anomalies = load_json_safe(ARTIFACTS_DIR / "anomalies.json")
    if anomalies:
        for anom in anomalies.get("anomalies", []):
            events.append({
                "source": "anomaly",
                "node": anom.get("node"),
                "metric": anom.get("metric"),
                "level": anom.get("severity"),
                "value": anom.get("current_value"),
                "z_score": anom.get("z_score"),
                "timestamp": anomalies.get("timestamp", ""),
            })

    # DR alerts
    dr_status = load_json_safe(DR_DIR / "dr_status.json")
    if dr_status and dr_status.get("status") != "GREEN":
        events.append({
            "source": "dr",
            "node": "cluster",
            "metric": "readiness",
            "level": "warning" if dr_status.get("status") == "YELLOW" else "critical",
            "value": dr_status.get("readiness_score"),
            "timestamp": dr_status.get("timestamp", ""),
        })

    # Forecast alerts
    forecast = load_json_safe(CAPACITY_DIR / "forecast.json")
    if forecast:
        for alert in forecast.get("alerts", []):
            events.append({
                "source": "forecast",
                "node": alert.get("node"),
                "metric": alert.get("metric"),
                "level": alert.get("level"),
                "value": alert.get("days_until_full"),
                "timestamp": forecast.get("timestamp", ""),
            })

    return events


def correlate(events):
    """Group related events into incident clusters."""
    policy = load_json_safe(CONFIG_DIR / "aiops_policy.json") or {}
    corr_cfg = policy.get("incident_correlation", {})
    min_events = corr_cfg.get("min_events_to_correlate", 2)

    # Group by node
    by_node = {}
    for e in events:
        node = e.get("node", "unknown")
        if node not in by_node:
            by_node[node] = []
        by_node[node].append(e)

    # Group by source (cross-node)
    by_source = {}
    for e in events:
        src = e.get("source", "unknown")
        if src not in by_source:
            by_source[src] = []
        by_source[src].append(e)

    incidents = []

    # Node-level incidents (multiple alerts on same node)
    for node, node_events in by_node.items():
        if len(node_events) >= min_events:
            incidents.append({
                "type": "node_incident",
                "node": node,
                "event_count": len(node_events),
                "sources": list(set(e["source"] for e in node_events)),
                "max_level": "critical" if any(e["level"] == "critical" for e in node_events) else "warning",
                "events": node_events,
            })

    # Cross-node incidents (same metric alert across multiple nodes)
    metric_nodes = {}
    for e in events:
        metric = e.get("metric", "unknown")
        node = e.get("node", "unknown")
        if metric not in metric_nodes:
            metric_nodes[metric] = set()
        metric_nodes[metric].add(node)

    for metric, nodes in metric_nodes.items():
        if len(nodes) >= min_events:
            incidents.append({
                "type": "cross_node",
                "metric": metric,
                "affected_nodes": sorted(nodes),
                "node_count": len(nodes),
                "max_level": "critical",
            })

    return incidents


def run_correlation():
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    events = collect_events()
    incidents = correlate(events)

    result = {
        "timestamp": timestamp,
        "total_events": len(events),
        "incidents": incidents,
        "incident_count": len(incidents),
    }

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(ARTIFACTS_DIR / "correlations.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


def main():
    parser = argparse.ArgumentParser(description="AIOps Incident Correlation")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = run_correlation()

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"🔗 Incident Correlation: {result['total_events']} events → {result['incident_count']} incidents")
        for inc in result["incidents"]:
            if inc["type"] == "node_incident":
                print(f"  🔴 {inc['node']}: {inc['event_count']} events ({', '.join(inc['sources'])})")
            elif inc["type"] == "cross_node":
                print(f"  🌐 {inc['metric']} affecting {inc['node_count']} nodes: {', '.join(inc['affected_nodes'])}")

        if not result["incidents"]:
            print("  ✅ No correlated incidents")

    sys.exit(0)


if __name__ == "__main__":
    main()
