#!/usr/bin/env python3
"""P36 — Observability Status Publisher: generate obs_status.json for dashboard."""

import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "artifacts" / "events"
DASHBOARD_DATA = ROOT / "dashboard" / "static" / "data"
CONFIG_DIR = ROOT / "config"


def load_json_safe(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def check_stack():
    """Check if Docker containers are running."""
    containers = {}
    expected = ["obs-prometheus", "obs-grafana", "obs-alertmanager", "obs-loki", "obs-node-exporter", "obs-promtail", "obs-cadvisor"]
    try:
        r = subprocess.run(["docker", "ps", "--format", "{{.Names}}:{{.Status}}"], capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            for line in r.stdout.strip().splitlines():
                parts = line.split(":", 1)
                if len(parts) == 2:
                    containers[parts[0]] = parts[1]
    except Exception:
        pass

    stack_status = {}
    for name in expected:
        status = containers.get(name, "not running")
        stack_status[name] = {
            "running": "Up" in status,
            "status": status,
        }
    return stack_status


def get_recent_events(limit=10):
    """Get most recent events."""
    events_file = ARTIFACTS_DIR / "events.jsonl"
    if not events_file.exists():
        return []
    lines = events_file.read_text().splitlines()
    events = []
    for line in lines[-limit:]:
        try:
            events.append(json.loads(line.strip()))
        except Exception:
            pass
    return events


def get_recent_alerts():
    """Check alertmanager for active alerts."""
    try:
        import requests
        r = requests.get("http://10.1.1.21:9093/api/v2/alerts", timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []


def publish():
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    policy = load_json_safe(CONFIG_DIR / "observability_policy.json") or {}

    stack = check_stack()
    running = sum(1 for s in stack.values() if s["running"])
    total = len(stack)

    events = get_recent_events(10)
    critical_events = [e for e in events if e.get("severity") == "critical"]

    if running == total:
        status = "GREEN"
    elif running > 0:
        status = "YELLOW"
    else:
        status = "RED"

    result = {
        "timestamp": timestamp,
        "status": status,
        "stack": {
            "running": running,
            "total": total,
            "containers": stack,
        },
        "events": {
            "recent_count": len(events),
            "critical_count": len(critical_events),
            "last_event": events[-1] if events else None,
        },
        "endpoints": {
            "prometheus": f"http://{policy.get('stack', {}).get('bind_address', '10.1.1.21')}:{policy.get('prometheus', {}).get('port', 9090)}",
            "grafana": f"http://{policy.get('stack', {}).get('bind_address', '10.1.1.21')}:{policy.get('grafana', {}).get('port', 3000)}",
            "alertmanager": f"http://{policy.get('stack', {}).get('bind_address', '10.1.1.21')}:{policy.get('alertmanager', {}).get('port', 9093)}",
        },
    }

    DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)
    with open(DASHBOARD_DATA / "obs_status.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


if __name__ == "__main__":
    result = publish()
    icon = "🟢" if result["status"] == "GREEN" else "🟡" if result["status"] == "YELLOW" else "🔴"
    print(f"{icon} Observability: {result['status']} ({result['stack']['running']}/{result['stack']['total']} containers)")
    print(f"  Events: {result['events']['recent_count']} recent, {result['events']['critical_count']} critical")
