#!/usr/bin/env python3
"""Cluster agent registry — tracks all agents, capabilities, and health state."""
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_FILE = ROOT / "data" / "cluster" / "agents" / "registry.json"

sys.path.insert(0, str(ROOT / "platform" / "events"))
from bus import emit as emit_event

VALID_STATUSES = ["online", "degraded", "offline", "maintenance"]
VALID_MODES = ["audit", "assisted", "autonomous_low_risk"]


def load_registry():
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if REGISTRY_FILE.exists():
        with open(REGISTRY_FILE) as f:
            return json.load(f)
    return {"agents": []}


def save_registry(data):
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_FILE, "w") as f:
        json.dump(data, f, indent=2)


def register_agent(agent_id, node_name, role, capabilities, execution_mode="audit",
                   hostname=None, version="1.0", service_account=None):
    """Register or update an agent in the registry."""
    data = load_registry()
    ts = datetime.now(timezone.utc).isoformat()

    existing = None
    for i, a in enumerate(data["agents"]):
        if a["agent_id"] == agent_id:
            existing = i
            break

    agent = {
        "agent_id": agent_id,
        "node_name": node_name,
        "role": role,
        "hostname": hostname or node_name,
        "status": "online",
        "capabilities": capabilities,
        "last_heartbeat": ts,
        "registered_at": ts,
        "version": version,
        "execution_mode": execution_mode if execution_mode in VALID_MODES else "audit",
        "service_account": service_account,
        "health_state": "healthy",
        "task_count": 0,
    }

    if existing is not None:
        agent["registered_at"] = data["agents"][existing].get("registered_at", ts)
        agent["task_count"] = data["agents"][existing].get("task_count", 0)
        data["agents"][existing] = agent
    else:
        data["agents"].append(agent)

    save_registry(data)
    emit_event("cluster.agent.registered", source="registry",
               payload={"agent_id": agent_id, "role": role, "node": node_name})
    return agent


def heartbeat(agent_id):
    """Update agent heartbeat timestamp."""
    data = load_registry()
    ts = datetime.now(timezone.utc).isoformat()
    for a in data["agents"]:
        if a["agent_id"] == agent_id:
            old_status = a["status"]
            a["last_heartbeat"] = ts
            if a["status"] in ("degraded", "offline"):
                a["status"] = "online"
                a["health_state"] = "healthy"
                emit_event("cluster.agent.state_changed", source="registry",
                           payload={"agent_id": agent_id, "old": old_status, "new": "online"})
            save_registry(data)
            emit_event("cluster.agent.heartbeat", source="registry",
                       payload={"agent_id": agent_id})
            return a
    return None


def set_status(agent_id, status, reason=None):
    """Set agent status."""
    if status not in VALID_STATUSES:
        return None
    data = load_registry()
    for a in data["agents"]:
        if a["agent_id"] == agent_id:
            old = a["status"]
            a["status"] = status
            if status == "offline":
                a["health_state"] = "unreachable"
            elif status == "degraded":
                a["health_state"] = "degraded"
            elif status == "online":
                a["health_state"] = "healthy"
            save_registry(data)
            if old != status:
                emit_event("cluster.agent.state_changed", source="registry",
                           payload={"agent_id": agent_id, "old": old, "new": status,
                                    "reason": reason})
            return a
    return None


def get_agent(agent_id):
    data = load_registry()
    for a in data["agents"]:
        if a["agent_id"] == agent_id:
            return a
    return None


def get_agents(status=None, role=None):
    data = load_registry()
    agents = data["agents"]
    if status:
        agents = [a for a in agents if a["status"] == status]
    if role:
        agents = [a for a in agents if a["role"] == role]
    return agents


def get_online_agents():
    return get_agents(status="online")


def get_agents_with_capability(capability):
    data = load_registry()
    return [a for a in data["agents"]
            if capability in a.get("capabilities", []) and a["status"] in ("online", "degraded")]


def summary():
    data = load_registry()
    agents = data["agents"]
    return {
        "total": len(agents),
        "online": len([a for a in agents if a["status"] == "online"]),
        "degraded": len([a for a in agents if a["status"] == "degraded"]),
        "offline": len([a for a in agents if a["status"] == "offline"]),
        "maintenance": len([a for a in agents if a["status"] == "maintenance"]),
    }


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "list":
        for a in get_agents():
            print(f"  {a['agent_id']:<10} {a['role']:<22} {a['status']:<10} {a['execution_mode']}")
    elif cmd == "summary":
        s = summary()
        print(f"  Agents: {s['total']} (online:{s['online']} degraded:{s['degraded']} offline:{s['offline']})")
    else:
        print("Usage: registry.py [list|summary]")


if __name__ == "__main__":
    main()
