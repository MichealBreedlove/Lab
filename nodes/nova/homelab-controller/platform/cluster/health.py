#!/usr/bin/env python3
"""Cluster health monitor — tracks heartbeats, marks degraded/offline, handles failover."""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
HEALTH_POLICY = ROOT / "config" / "cluster_health_policy.json"

sys.path.insert(0, str(ROOT / "platform" / "cluster"))
sys.path.insert(0, str(ROOT / "platform" / "events"))
from registry import load_registry, save_registry, set_status, get_agents
from task_bus import get_tasks, reassign_task
from router import route_task
from bus import emit as emit_event


def load_health_policy():
    if HEALTH_POLICY.exists():
        with open(HEALTH_POLICY) as f:
            return json.load(f)
    return {"degraded_after_seconds": 90, "offline_after_seconds": 180,
            "auto_reassign_low_risk_tasks": True, "auto_reassign_high_risk_tasks": False}


def check_agent_health():
    """Check all agents for missed heartbeats. Returns list of state changes."""
    policy = load_health_policy()
    degraded_threshold = timedelta(seconds=policy.get("degraded_after_seconds", 90))
    offline_threshold = timedelta(seconds=policy.get("offline_after_seconds", 180))
    now = datetime.now(timezone.utc)
    changes = []

    data = load_registry()
    for agent in data["agents"]:
        if agent["status"] == "maintenance":
            continue
        last_hb = agent.get("last_heartbeat")
        if not last_hb:
            continue
        try:
            hb_time = datetime.fromisoformat(last_hb)
        except (ValueError, TypeError):
            continue

        age = now - hb_time
        old_status = agent["status"]

        if age > offline_threshold and old_status != "offline":
            set_status(agent["agent_id"], "offline", "Heartbeat timeout")
            emit_event("cluster.agent.offline", source="health_monitor",
                       payload={"agent_id": agent["agent_id"], "last_heartbeat": last_hb})
            changes.append({"agent_id": agent["agent_id"], "old": old_status, "new": "offline"})
        elif age > degraded_threshold and old_status == "online":
            set_status(agent["agent_id"], "degraded", "Heartbeat delayed")
            emit_event("cluster.agent.degraded", source="health_monitor",
                       payload={"agent_id": agent["agent_id"], "last_heartbeat": last_hb})
            changes.append({"agent_id": agent["agent_id"], "old": old_status, "new": "degraded"})

    return changes


def reassign_orphaned_tasks():
    """Reassign tasks from offline agents to fallback agents."""
    policy = load_health_policy()
    auto_low = policy.get("auto_reassign_low_risk_tasks", True)
    auto_high = policy.get("auto_reassign_high_risk_tasks", False)
    reassigned = []

    tasks = get_tasks(status="assigned") + get_tasks(status="running")
    offline_agents = {a["agent_id"] for a in get_agents(status="offline")}

    for task in tasks:
        assigned = task.get("assigned_to")
        if assigned not in offline_agents:
            continue

        # Check risk level from policy context
        risk = task.get("policy_context", {}).get("risk_level", "low")
        if risk in ("high",) and not auto_high:
            continue
        if risk in ("medium", "low") and not auto_low:
            continue

        # Find fallback
        new_agent, reason = route_task(task["task_type"])
        if new_agent and new_agent != assigned and new_agent not in offline_agents:
            reassign_task(task["task_id"], new_agent)
            reassigned.append({"task_id": task["task_id"], "from": assigned, "to": new_agent})

    return reassigned


def health_tick():
    """Run one health check cycle."""
    changes = check_agent_health()
    reassigned = reassign_orphaned_tasks()
    return {"state_changes": changes, "reassigned_tasks": reassigned}


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "check":
        result = health_tick()
        print(f"  State changes: {len(result['state_changes'])}")
        print(f"  Reassigned: {len(result['reassigned_tasks'])}")
        for c in result["state_changes"]:
            print(f"    {c['agent_id']}: {c['old']} -> {c['new']}")
    else:
        print("Usage: health.py [check]")


if __name__ == "__main__":
    main()
