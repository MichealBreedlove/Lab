#!/usr/bin/env python3
"""Cluster task bus — structured task delegation between agents."""
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TASKS_FILE = ROOT / "data" / "cluster" / "tasks" / "tasks.json"

sys.path.insert(0, str(ROOT / "platform" / "events"))
from bus import emit as emit_event

VALID_STATUSES = ["queued", "assigned", "running", "completed", "failed", "timed_out", "denied"]
VALID_PRIORITIES = ["low", "normal", "high", "critical"]


def load_tasks():
    TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if TASKS_FILE.exists():
        with open(TASKS_FILE) as f:
            return json.load(f)
    return {"tasks": []}


def save_tasks(data):
    TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TASKS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def create_task(task_type, source_agent, target_agent=None, target_role=None,
                priority="normal", payload=None, timeout_seconds=300, max_retries=1,
                policy_context=None):
    """Create a new task on the bus."""
    ts = datetime.now(timezone.utc)
    task_id = f"TASK-{ts.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    task = {
        "task_id": task_id,
        "created_at": ts.isoformat(),
        "source_agent": source_agent,
        "target_agent": target_agent,
        "target_role": target_role,
        "task_type": task_type,
        "priority": priority if priority in VALID_PRIORITIES else "normal",
        "payload": payload or {},
        "status": "queued",
        "policy_context": policy_context or {},
        "timeout_seconds": timeout_seconds,
        "retry_count": 0,
        "max_retries": max_retries,
        "assigned_to": None,
        "assigned_at": None,
        "completed_at": None,
        "result": None,
    }
    data = load_tasks()
    data["tasks"].append(task)
    save_tasks(data)
    emit_event("cluster.task.created", source="task_bus",
               payload={"task_id": task_id, "type": task_type, "target_role": target_role})
    return task


def claim_task(agent_id, agent_capabilities, agent_role):
    """Claim the next eligible queued task for an agent."""
    data = load_tasks()
    ts = datetime.now(timezone.utc).isoformat()
    for task in data["tasks"]:
        if task["status"] != "queued":
            continue
        # Check target_agent match
        if task.get("target_agent") and task["target_agent"] != agent_id:
            continue
        # Check target_role match
        if task.get("target_role") and task["target_role"] != agent_role:
            # Also check capabilities
            if task["task_type"] not in agent_capabilities:
                continue

        task["status"] = "assigned"
        task["assigned_to"] = agent_id
        task["assigned_at"] = ts
        save_tasks(data)
        emit_event("cluster.task.assigned", source="task_bus",
                   payload={"task_id": task["task_id"], "agent_id": agent_id})
        return task
    return None


def start_task(task_id, agent_id):
    """Mark a task as running."""
    data = load_tasks()
    for task in data["tasks"]:
        if task["task_id"] == task_id and task["assigned_to"] == agent_id:
            task["status"] = "running"
            save_tasks(data)
            return task
    return None


def complete_task(task_id, agent_id, result):
    """Complete a task with result."""
    data = load_tasks()
    ts = datetime.now(timezone.utc).isoformat()
    for task in data["tasks"]:
        if task["task_id"] == task_id and task["assigned_to"] == agent_id:
            task["status"] = "completed"
            task["completed_at"] = ts
            task["result"] = result
            save_tasks(data)
            emit_event("cluster.task.completed", source="task_bus",
                       payload={"task_id": task_id, "agent_id": agent_id,
                                "result_type": result.get("result_type", "unknown")})
            return task
    return None


def fail_task(task_id, agent_id, error):
    """Fail a task."""
    data = load_tasks()
    ts = datetime.now(timezone.utc).isoformat()
    for task in data["tasks"]:
        if task["task_id"] == task_id:
            task["status"] = "failed"
            task["completed_at"] = ts
            task["retry_count"] = task.get("retry_count", 0) + 1
            task["result"] = {"error": error}
            # Re-queue if retries remain
            if task["retry_count"] < task.get("max_retries", 1):
                task["status"] = "queued"
                task["assigned_to"] = None
                task["assigned_at"] = None
            save_tasks(data)
            emit_event("cluster.task.failed", source="task_bus",
                       payload={"task_id": task_id, "agent_id": agent_id, "error": error})
            return task
    return None


def reassign_task(task_id, new_agent_id):
    """Reassign a task to a different agent."""
    data = load_tasks()
    ts = datetime.now(timezone.utc).isoformat()
    for task in data["tasks"]:
        if task["task_id"] == task_id:
            old_agent = task.get("assigned_to")
            task["status"] = "queued"
            task["assigned_to"] = None
            task["assigned_at"] = None
            task["target_agent"] = new_agent_id
            save_tasks(data)
            emit_event("cluster.task.reassigned", source="task_bus",
                       payload={"task_id": task_id, "from": old_agent, "to": new_agent_id})
            return task
    return None


def get_tasks(status=None, agent_id=None, limit=50):
    data = load_tasks()
    tasks = data["tasks"]
    if status:
        tasks = [t for t in tasks if t["status"] == status]
    if agent_id:
        tasks = [t for t in tasks if t.get("assigned_to") == agent_id or t.get("source_agent") == agent_id]
    return tasks[-limit:]


def task_summary():
    data = load_tasks()
    tasks = data["tasks"]
    return {
        "total": len(tasks),
        "queued": len([t for t in tasks if t["status"] == "queued"]),
        "assigned": len([t for t in tasks if t["status"] == "assigned"]),
        "running": len([t for t in tasks if t["status"] == "running"]),
        "completed": len([t for t in tasks if t["status"] == "completed"]),
        "failed": len([t for t in tasks if t["status"] == "failed"]),
    }


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "list":
        for t in get_tasks():
            print(f"  {t['task_id']:<30} {t['task_type']:<22} {t['status']:<12} {t.get('assigned_to','?')}")
    elif cmd == "summary":
        s = task_summary()
        print(f"  Tasks: {s['total']} (Q:{s['queued']} A:{s['assigned']} R:{s['running']} C:{s['completed']} F:{s['failed']})")
    else:
        print("Usage: task_bus.py [list|summary]")


if __name__ == "__main__":
    main()
