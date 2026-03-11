#!/usr/bin/env python3
"""
check_state.py — reads STATE.yaml and reports queued tasks.
Called by Jasper during heartbeats to decide if sub-agent work should be spawned.

Exit codes:
  0 = nothing queued
  1 = tasks queued (stdout has summary)
"""
import sys
import yaml
from pathlib import Path

STATE_FILE = Path(r"C:\Users\mikej\.openclaw\workspace\STATE.yaml")

def main():
    if not STATE_FILE.exists():
        sys.exit(0)

    state = yaml.safe_load(STATE_FILE.read_text())
    queued = []

    for goal in state.get("goals", []):
        for task in goal.get("tasks", []):
            if task.get("status") == "queued":
                queued.append({
                    "goal": goal["title"],
                    "task": task["title"],
                    "id": task["id"],
                    "agent": task.get("agent", "any"),
                    "notes": task.get("notes", ""),
                })

    if not queued:
        sys.exit(0)

    print(f"{len(queued)} queued task(s) in STATE.yaml:\n")
    for t in queued:
        print(f"  [{t['id']}] {t['goal']} -> {t['task']}")
        if t["notes"]:
            print(f"      Notes: {t['notes']}")
        print(f"      Agent: {t['agent']}")
    sys.exit(1)

if __name__ == "__main__":
    main()
