#!/usr/bin/env python3
"""Capability router — routes tasks to the correct agent based on role, health, and policy."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
ROUTING_POLICY = ROOT / "config" / "cluster_routing_policy.json"

sys.path.insert(0, str(ROOT / "platform" / "cluster"))
from registry import get_agents, get_agent


def load_routing_policy():
    if ROUTING_POLICY.exists():
        with open(ROUTING_POLICY) as f:
            return json.load(f)
    return {"enabled": True, "roles": {}, "task_routing": {}, "fallback_order": {}}


def find_agent_for_role(role):
    """Find the primary agent assigned to a role."""
    policy = load_routing_policy()
    for agent_id, roles in policy.get("roles", {}).items():
        if role in roles:
            return agent_id
    return None


def route_task(task_type, preferred_agent=None):
    """Route a task to the best available agent.

    Returns (agent_id, reason) or (None, reason).
    """
    policy = load_routing_policy()
    if not policy.get("enabled", True):
        return None, "Routing policy disabled"

    # If preferred agent specified and online, use it
    if preferred_agent:
        agent = get_agent(preferred_agent)
        if agent and agent["status"] in ("online", "degraded"):
            return preferred_agent, f"Preferred agent '{preferred_agent}' available"

    # Look up task type -> role mapping
    task_routing = policy.get("task_routing", {})
    target_role = task_routing.get(task_type)

    if not target_role:
        return "jasper", f"No routing rule for '{task_type}', defaulting to coordinator"

    # Get fallback order for this role
    fallback = policy.get("fallback_order", {}).get(target_role, [])
    if not fallback:
        # Try to find agent for role directly
        agent_id = find_agent_for_role(target_role)
        if agent_id:
            fallback = [agent_id]
        else:
            return "jasper", f"No fallback for role '{target_role}', defaulting to coordinator"

    # Try each agent in fallback order
    for agent_id in fallback:
        agent = get_agent(agent_id)
        if agent and agent["status"] in ("online", "degraded"):
            return agent_id, f"Routed to '{agent_id}' (role: {target_role})"

    return None, f"No available agents for role '{target_role}'"


def route_to_capability(capability):
    """Find an agent with a specific capability."""
    from registry import get_agents_with_capability
    agents = get_agents_with_capability(capability)
    if agents:
        # Prefer online over degraded
        online = [a for a in agents if a["status"] == "online"]
        if online:
            return online[0]["agent_id"], f"Agent '{online[0]['agent_id']}' has capability '{capability}'"
        return agents[0]["agent_id"], f"Degraded agent '{agents[0]['agent_id']}' has capability '{capability}'"
    return None, f"No agent with capability '{capability}'"


def get_cluster_workload():
    """Get current workload distribution."""
    agents = get_agents()
    workload = {}
    for a in agents:
        workload[a["agent_id"]] = {
            "status": a["status"],
            "role": a["role"],
            "task_count": a.get("task_count", 0),
        }
    return workload


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "route":
        task_type = sys.argv[2] if len(sys.argv) > 2 else "audit_firewall"
        agent_id, reason = route_task(task_type)
        print(f"  Task: {task_type}")
        print(f"  Agent: {agent_id or 'NONE'}")
        print(f"  Reason: {reason}")
    elif cmd == "workload":
        wl = get_cluster_workload()
        for aid, info in wl.items():
            print(f"  {aid:<10} {info['role']:<22} {info['status']:<10} tasks:{info['task_count']}")
    else:
        print("Usage: router.py [route <task_type>|workload]")


if __name__ == "__main__":
    main()
