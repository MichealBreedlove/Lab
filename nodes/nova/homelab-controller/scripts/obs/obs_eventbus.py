#!/usr/bin/env python3
"""P36 — Event Bus: unified internal event schema + writer for all subsystems."""

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "artifacts" / "events"
CONFIG_DIR = ROOT / "config"

EVENT_TYPES = [
    "snapshot.created", "snapshot.stale",
    "planner.plan.generated", "planner.plan.executed",
    "gate.approved", "gate.denied",
    "action.executed", "action.failed",
    "incident.opened", "incident.resolved",
    "dr.drill.completed", "dr.restore.started", "dr.restore.completed",
    "slo.burn.high", "slo.burn.normal",
    "bootstrap.completed", "bootstrap.failed",
    "capacity.alert", "capacity.forecast",
    "obs.stack.up", "obs.stack.down",
    "security.scan.clean", "security.scan.violation",
    "infra.backup.completed",
    "portfolio.exported",
]

SEVERITIES = ["info", "warning", "critical"]


def load_json_safe(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def write_event(event_type, severity="info", node=None, component=None, message="", context=None):
    """Write a single event to the event bus (JSONL file)."""
    policy = load_json_safe(CONFIG_DIR / "observability_policy.json") or {}
    bus_cfg = policy.get("eventbus", {})

    if not bus_cfg.get("enabled", True):
        return None

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    events_file = ARTIFACTS_DIR / "events.jsonl"

    event = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "type": event_type,
        "severity": severity,
        "node": node,
        "component": component,
        "message": message,
    }
    if context:
        event["context"] = context

    with open(events_file, "a") as f:
        f.write(json.dumps(event) + "\n")

    # Rotate if too large
    max_mb = bus_cfg.get("max_file_mb", 50)
    try:
        size_mb = events_file.stat().st_size / (1024 * 1024)
        if size_mb > max_mb:
            rotated = ARTIFACTS_DIR / f"events_{int(time.time())}.jsonl"
            events_file.rename(rotated)
    except Exception:
        pass

    return event


def read_events(limit=50, event_type=None, severity=None):
    """Read recent events from the bus."""
    events_file = ARTIFACTS_DIR / "events.jsonl"
    if not events_file.exists():
        return []

    events = []
    for line in events_file.read_text().splitlines():
        try:
            e = json.loads(line.strip())
            if event_type and e.get("type") != event_type:
                continue
            if severity and e.get("severity") != severity:
                continue
            events.append(e)
        except json.JSONDecodeError:
            continue

    return events[-limit:]


def main():
    parser = argparse.ArgumentParser(description="Event Bus")
    sub = parser.add_subparsers(dest="command")

    # Write event
    w = sub.add_parser("write", help="Write an event")
    w.add_argument("--type", required=True, choices=EVENT_TYPES)
    w.add_argument("--severity", default="info", choices=SEVERITIES)
    w.add_argument("--node", default=None)
    w.add_argument("--component", default=None)
    w.add_argument("--message", default="")

    # Read events
    r = sub.add_parser("read", help="Read recent events")
    r.add_argument("--limit", type=int, default=20)
    r.add_argument("--type", default=None)
    r.add_argument("--severity", default=None)
    r.add_argument("--json", action="store_true")

    # List types
    sub.add_parser("types", help="List event types")

    args = parser.parse_args()

    if args.command == "write":
        event = write_event(args.type, args.severity, args.node, args.component, args.message)
        if event:
            print(f"✅ Event written: {event['type']} ({event['severity']})")
        else:
            print("⏭️  Event bus disabled")

    elif args.command == "read":
        events = read_events(args.limit, args.type, args.severity)
        if hasattr(args, 'json') and args.json:
            print(json.dumps(events, indent=2))
        else:
            print(f"📋 Last {len(events)} events:")
            for e in events:
                icon = "🔴" if e["severity"] == "critical" else "🟡" if e["severity"] == "warning" else "ℹ️"
                print(f"  {icon} [{e['timestamp'][:19]}] {e['type']}: {e.get('message', '')}")

    elif args.command == "types":
        print("Event types:")
        for t in EVENT_TYPES:
            print(f"  • {t}")

    else:
        parser.print_help()

    sys.exit(0)


if __name__ == "__main__":
    main()
