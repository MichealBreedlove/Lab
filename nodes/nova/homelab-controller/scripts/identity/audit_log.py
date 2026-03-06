#!/usr/bin/env python3
"""Audit log for homelab control plane identity layer."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
AUDIT_DIR = ROOT / "artifacts" / "identity" / "audit"
LATEST_JSON = ROOT / "artifacts" / "identity" / "audit_latest.json"
LATEST_MD = ROOT / "artifacts" / "identity" / "audit_latest.md"


def append_event(event_type, actor="system", target="", details=None, result="success"):
    """Append a structured audit event."""
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc)
    date_str = ts.strftime("%Y-%m-%d")
    log_file = AUDIT_DIR / f"audit_{date_str}.jsonl"

    event = {
        "timestamp": ts.isoformat(),
        "event_type": event_type,
        "actor": actor,
        "target": target,
        "result": result,
        "details": details or {},
    }

    with open(log_file, "a") as f:
        f.write(json.dumps(event) + "\n")

    return event


def get_today_events():
    """Get all audit events from today."""
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = AUDIT_DIR / f"audit_{date_str}.jsonl"
    events = []
    if log_file.exists():
        with open(log_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
    return events


def generate_summary():
    """Generate summary JSON and markdown from today's audit events."""
    events = get_today_events()
    LATEST_JSON.parent.mkdir(parents=True, exist_ok=True)

    # Count by type
    by_type = {}
    failed = 0
    for e in events:
        t = e.get("event_type", "unknown")
        by_type[t] = by_type.get(t, 0) + 1
        if e.get("result") != "success":
            failed += 1

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_events": len(events),
        "failed_events": failed,
        "by_type": by_type,
        "latest_event": events[-1] if events else None,
    }

    with open(LATEST_JSON, "w") as f:
        json.dump(summary, f, indent=2)

    lines = [
        "# Audit Summary",
        "",
        f"Generated: {summary['timestamp']}",
        f"Total events: {len(events)}",
        f"Failed: {failed}",
        "",
        "## Events by Type",
        "",
        "| Type | Count |",
        "|------|-------|",
    ]
    for t, c in sorted(by_type.items()):
        lines.append(f"| {t} | {c} |")

    if events:
        lines.extend([
            "",
            "## Recent Events (last 10)",
            "",
            "| Time | Type | Actor | Result |",
            "|------|------|-------|--------|",
        ])
        for e in events[-10:]:
            ts = e["timestamp"][:19]
            lines.append(f"| {ts} | {e['event_type']} | {e['actor']} | {e['result']} |")

    with open(LATEST_MD, "w") as f:
        f.write("\n".join(lines) + "\n")

    print(f"[OK] Audit summary: {len(events)} events, {failed} failed")
    return summary


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "summary"

    if cmd == "log":
        event_type = sys.argv[2] if len(sys.argv) > 2 else "manual"
        actor = sys.argv[3] if len(sys.argv) > 3 else "cli"
        target = sys.argv[4] if len(sys.argv) > 4 else ""
        result = sys.argv[5] if len(sys.argv) > 5 else "success"
        event = append_event(event_type, actor=actor, target=target, result=result)
        print(f"[OK] Audit event logged: {event['event_type']}")
    elif cmd == "summary":
        generate_summary()
    elif cmd == "recent":
        events = get_today_events()
        for e in events[-20:]:
            ts = e["timestamp"][:19]
            print(f"  {ts}  {e['event_type']:<20} {e['actor']:<12} {e['result']}")
        if not events:
            print("  No audit events today.")
    else:
        print("Usage: audit_log.py [log <type> <actor> <target> <result>|summary|recent]")


if __name__ == "__main__":
    main()
