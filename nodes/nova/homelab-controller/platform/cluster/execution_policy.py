#!/usr/bin/env python3
"""Distributed execution policy — gates task execution by role, capability, and risk."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
POLICY_FILE = ROOT / "config" / "distributed_execution_policy.json"

sys.path.insert(0, str(ROOT / "platform" / "cluster"))
from registry import get_agent


def load_policy():
    if POLICY_FILE.exists():
        with open(POLICY_FILE) as f:
            return json.load(f)
    return {"enabled": True, "auto_allow_task_types": [], "require_review_task_types": [],
            "deny_task_types": [], "capability_enforcement": True}


def evaluate_task_execution(agent_id, task_type, task_payload=None):
    """Evaluate whether an agent can execute a task.

    Returns: ("allow"|"deny"|"require_review", reason)
    """
    policy = load_policy()
    if not policy.get("enabled", True):
        return "deny", "Distributed execution policy disabled"

    agent = get_agent(agent_id)
    if not agent:
        return "deny", f"Agent '{agent_id}' not registered"

    if agent["status"] == "offline":
        return "deny", f"Agent '{agent_id}' is offline"

    # Check deny list
    if task_type in policy.get("deny_task_types", []):
        return "deny", f"Task type '{task_type}' is denied by policy"

    # Check capability enforcement
    if policy.get("capability_enforcement", True):
        capabilities = agent.get("capabilities", [])
        # Map task types to capabilities
        task_cap_map = {
            "audit_firewall": "firewall_audit",
            "audit_wifi": "wifi_analysis",
            "audit_proxmox": "cluster_scan",
            "cluster_scan": "cluster_scan",
            "detect_drift": "network_drift_detection",
            "analyze_logs": "log_analysis",
            "anomaly_detection": "anomaly_detection",
            "investigate_incident": "incident_investigation",
            "optimize_backups": "backup_audit",
        }
        required_cap = task_cap_map.get(task_type)
        if required_cap and required_cap not in capabilities:
            # Check if task_type itself is in capabilities
            if task_type not in capabilities:
                return "deny", f"Agent '{agent_id}' lacks capability for '{task_type}'"

    # Check mode restrictions
    mode = agent.get("execution_mode", "audit")
    mode_allowed = policy.get("mode_restrictions", {}).get(mode, [])
    if mode_allowed and task_type not in mode_allowed:
        return "deny", f"Task '{task_type}' not allowed in '{mode}' mode"

    # Check require_review list
    if task_type in policy.get("require_review_task_types", []):
        return "require_review", f"Task '{task_type}' requires review"

    # Auto-allow
    if task_type in policy.get("auto_allow_task_types", []):
        return "allow", f"Task '{task_type}' auto-allowed"

    # Default to require_review
    return "require_review", f"Task '{task_type}' defaults to review"


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "evaluate":
        agent = sys.argv[2] if len(sys.argv) > 2 else "jasper"
        task = sys.argv[3] if len(sys.argv) > 3 else "audit_firewall"
        decision, reason = evaluate_task_execution(agent, task)
        print(f"  Agent: {agent}")
        print(f"  Task: {task}")
        print(f"  Decision: {decision}")
        print(f"  Reason: {reason}")
    else:
        print("Usage: execution_policy.py evaluate <agent_id> <task_type>")


if __name__ == "__main__":
    main()
