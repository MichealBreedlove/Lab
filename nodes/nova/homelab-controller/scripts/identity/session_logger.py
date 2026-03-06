#!/usr/bin/env python3
"""Session logger for homelab control plane."""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
LOG_DIR = ROOT / "artifacts" / "identity" / "sessions"


def log_session(user="unknown", token_id=None, command="", target="",
                result="success", source_ip="", details=None):
    """Log a session event."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc)
    date_str = ts.strftime("%Y-%m-%d")
    log_file = LOG_DIR / f"sessions_{date_str}.jsonl"

    entry = {
        "timestamp": ts.isoformat(),
        "user": user,
        "token_id": token_id,
        "command": command,
        "target": target,
        "result": result,
        "source_ip": source_ip,
        "details": details or {},
    }

    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")

    return entry


def get_recent(count=20, date=None):
    """Get recent session entries."""
    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    log_file = LOG_DIR / f"sessions_{date}.jsonl"
    entries = []
    if log_file.exists():
        with open(log_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))

    return entries[-count:]


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "recent"

    if cmd == "log":
        user = sys.argv[2] if len(sys.argv) > 2 else "cli"
        command = sys.argv[3] if len(sys.argv) > 3 else ""
        result = sys.argv[4] if len(sys.argv) > 4 else "success"
        entry = log_session(user=user, command=command, result=result)
        print(f"[OK] Session logged: {entry['timestamp']}")
    elif cmd == "recent":
        entries = get_recent()
        for e in entries:
            ts = e["timestamp"][:19]
            print(f"  {ts}  {e['user']:<12} {e['command']:<30} {e['result']}")
        if not entries:
            print("  No sessions recorded today.")
    else:
        print("Usage: session_logger.py [log <user> <command> <result>|recent]")


if __name__ == "__main__":
    main()
