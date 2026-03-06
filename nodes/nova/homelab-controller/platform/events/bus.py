#!/usr/bin/env python3
"""Internal event bus — append-only JSONL event store."""
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
EVENT_LOG = ROOT / "data" / "events" / "event_log.jsonl"

VALID_TYPES = [
    "incident.created", "incident.updated", "incident.confirmed",
    "recovery.started", "recovery.completed", "recovery.failed",
    "ai.investigation.started", "ai.investigation.completed",
    "ai.remediation.proposed", "ai.remediation.artifact_created",
]


def emit(event_type, source="system", incident_id=None, payload=None):
    """Emit an event to the bus. Returns event dict."""
    EVENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc)
    seq = ts.strftime("%Y%m%d-%H%M%S")
    event = {
        "event_id": f"EVT-{seq}-{uuid.uuid4().hex[:6]}",
        "event_type": event_type,
        "incident_id": incident_id,
        "timestamp": ts.isoformat(),
        "source": source,
        "payload": payload or {},
    }
    with open(EVENT_LOG, "a") as f:
        f.write(json.dumps(event) + "\n")
    return event


def query(event_type=None, incident_id=None, limit=50):
    """Query events with optional filters."""
    if not EVENT_LOG.exists():
        return []
    events = []
    with open(EVENT_LOG) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event_type and e.get("event_type") != event_type:
                continue
            if incident_id and e.get("incident_id") != incident_id:
                continue
            events.append(e)
    return events[-limit:]


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "emit":
        etype = sys.argv[2] if len(sys.argv) > 2 else "incident.created"
        source = sys.argv[3] if len(sys.argv) > 3 else "cli"
        inc_id = sys.argv[4] if len(sys.argv) > 4 else None
        ev = emit(etype, source=source, incident_id=inc_id)
        print(f"[OK] Event emitted: {ev['event_id']} ({etype})")
    elif cmd == "list":
        etype = None
        inc_id = None
        lim = 20
        args = sys.argv[2:]
        i = 0
        while i < len(args):
            if args[i] == "--type" and i + 1 < len(args):
                etype = args[i + 1]; i += 2
            elif args[i] == "--incident" and i + 1 < len(args):
                inc_id = args[i + 1]; i += 2
            elif args[i] == "--limit" and i + 1 < len(args):
                lim = int(args[i + 1]); i += 2
            else:
                i += 1
        events = query(event_type=etype, incident_id=inc_id, limit=lim)
        for e in events:
            ts = e["timestamp"][:19]
            inc = e.get("incident_id") or "-"
            print(f"  {ts}  {e['event_type']:<35} {inc:<30} {e['source']}")
        if not events:
            print("  No events.")
    else:
        print("Usage: bus.py [emit <type> <source> [incident_id]|list [--type X] [--incident X] [--limit N]]")


if __name__ == "__main__":
    main()
