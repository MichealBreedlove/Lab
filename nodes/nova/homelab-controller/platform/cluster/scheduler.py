#!/usr/bin/env python3
"""Cluster scheduler — creates tasks on schedule for the distributed operations loop."""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SCHEDULE_FILE = ROOT / "config" / "cluster_schedule.json"
STATE_FILE = ROOT / "data" / "cluster" / "scheduler_state.json"
SCORECARD_DIR = ROOT / "data" / "reports"

sys.path.insert(0, str(ROOT / "platform" / "cluster"))
from task_bus import create_task, task_summary
from registry import summary as agent_summary


def load_schedule():
    if SCHEDULE_FILE.exists():
        with open(SCHEDULE_FILE) as f:
            return json.load(f)
    return {"enabled": True, "schedules": []}


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_run": {}}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def should_run(schedule_name, interval_minutes, state):
    """Check if a scheduled task is due."""
    last = state.get("last_run", {}).get(schedule_name)
    if not last:
        return True
    try:
        last_time = datetime.fromisoformat(last)
        return datetime.now(timezone.utc) - last_time > timedelta(minutes=interval_minutes)
    except (ValueError, TypeError):
        return True


def tick():
    """Run one scheduler cycle — create tasks that are due."""
    config = load_schedule()
    if not config.get("enabled", True):
        return {"created": 0, "tasks": []}

    state = load_state()
    created = []

    for sched in config.get("schedules", []):
        name = sched["name"]
        interval = sched.get("interval_minutes", 1440)
        if not should_run(name, interval, state):
            continue

        task = create_task(
            task_type=sched["task_type"],
            source_agent="scheduler",
            target_role=sched.get("target_role"),
            priority=sched.get("priority", "normal"),
            payload=sched.get("payload", {}),
            timeout_seconds=sched.get("timeout_seconds", 300),
        )
        created.append(task)

        if "last_run" not in state:
            state["last_run"] = {}
        state["last_run"][name] = datetime.now(timezone.utc).isoformat()

    save_state(state)
    return {"created": len(created), "tasks": created}


def generate_scorecard():
    """Generate daily infrastructure scorecard."""
    SCORECARD_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc)
    agents = agent_summary()
    tasks = task_summary()

    # Score computation (simple heuristic)
    agent_score = min(100, (agents["online"] / max(agents["total"], 1)) * 100)
    task_score = min(100, (tasks["completed"] / max(tasks["total"], 1)) * 100) if tasks["total"] > 0 else 100

    scorecard = {
        "timestamp": ts.isoformat(),
        "scores": {
            "cluster_health": round(agent_score, 1),
            "task_completion": round(task_score, 1),
            "automation_maturity": 75,  # baseline for having the system
        },
        "agents": agents,
        "tasks": tasks,
    }

    # Write JSON
    json_file = SCORECARD_DIR / f"scorecard_{ts.strftime('%Y%m%d')}.json"
    with open(json_file, "w") as f:
        json.dump(scorecard, f, indent=2)

    # Write markdown
    md_file = SCORECARD_DIR / "daily_scorecard.md"
    with open(md_file, "w") as f:
        f.write(f"# Daily Infrastructure Scorecard\n\n")
        f.write(f"Generated: {ts.strftime('%Y-%m-%d %H:%M UTC')}\n\n")
        f.write(f"## Scores\n\n")
        for name, score in scorecard["scores"].items():
            f.write(f"- **{name.replace('_', ' ').title()}**: {score}%\n")
        f.write(f"\n## Cluster\n\n")
        f.write(f"- Online: {agents['online']}/{agents['total']}\n")
        f.write(f"- Degraded: {agents['degraded']}\n")
        f.write(f"- Offline: {agents['offline']}\n")
        f.write(f"\n## Tasks (24h)\n\n")
        f.write(f"- Completed: {tasks['completed']}\n")
        f.write(f"- Failed: {tasks['failed']}\n")
        f.write(f"- Queued: {tasks['queued']}\n")

    return scorecard


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "tick"
    if cmd == "tick":
        result = tick()
        print(f"[OK] Scheduler tick: {result['created']} tasks created")
    elif cmd == "scorecard":
        sc = generate_scorecard()
        print(f"[OK] Scorecard generated")
        for name, score in sc["scores"].items():
            print(f"  {name}: {score}%")
    elif cmd == "status":
        state = load_state()
        print("  Last runs:")
        for name, ts in state.get("last_run", {}).items():
            print(f"    {name}: {ts}")
    else:
        print("Usage: scheduler.py [tick|scorecard|status]")


if __name__ == "__main__":
    main()
