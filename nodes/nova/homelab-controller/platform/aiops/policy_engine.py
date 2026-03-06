#!/usr/bin/env python3
"""Execution policy engine — evaluates remediation decisions against safety rules."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
POLICY_FILE = ROOT / "config" / "aiops_policy.json"
AUDIT_FILE = ROOT / "artifacts" / "identity" / "policy_audit.jsonl"

sys.path.insert(0, str(ROOT / "platform" / "events"))
from bus import emit as emit_event

# Role rank for authorization checks
ROLE_RANK = {"viewer": 0, "operator": 1, "automation": 1, "sre": 2, "admin": 3}

# Minimum role required to execute actions by risk level
RISK_MIN_ROLE = {
    "low": "operator",
    "medium": "sre",
    "high": "admin",
}


def load_policy():
    """Load AIOps policy configuration."""
    if POLICY_FILE.exists():
        with open(POLICY_FILE) as f:
            return json.load(f)
    return {
        "enabled": True,
        "confidence_thresholds": {"auto_apply": 0.90, "requires_review": 0.80},
        "action_risk_levels": {},
        "high_risk_actions": [],
        "auto_apply_actions": [],
    }


def get_action_risk(action, policy=None):
    """Get risk level for an action."""
    if policy is None:
        policy = load_policy()
    levels = policy.get("action_risk_levels", {})
    if action in levels:
        return levels[action]
    if action in policy.get("high_risk_actions", []):
        return "high"
    return "medium"


def is_reversible(action):
    """Determine if an action is reversible."""
    reversible_actions = {"restart_service", "rollback_config", "failover_service"}
    irreversible_actions = {"delete_data", "mass_config_rewrite"}
    if action in reversible_actions:
        return True
    if action in irreversible_actions:
        return False
    return True  # default to reversible for unknown actions


def compute_blast_radius(action, risk_level):
    """Compute blast radius from action and risk level."""
    if risk_level == "high":
        return "high"
    if risk_level == "medium":
        return "medium"
    return "low"


def audit_policy_decision(decision, details):
    """Append a policy evaluation to the audit log."""
    AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        **details,
    }
    with open(AUDIT_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def evaluate_remediation_policy(action, confidence, role="operator", incident_id=None):
    """Evaluate whether a remediation action is allowed.

    Returns dict with:
        decision: "auto_apply" | "require_review" | "deny_execution"
        approval_required: bool
        blast_radius: "low" | "medium" | "high"
        reversible: bool
        reason: str
    """
    policy = load_policy()

    if not policy.get("enabled", True):
        result = {
            "decision": "deny_execution",
            "approval_required": True,
            "blast_radius": "unknown",
            "reversible": False,
            "reason": "AIOps policy is disabled",
        }
        audit_policy_decision("deny_execution", {
            "action": action, "confidence": confidence, "role": role,
            "incident_id": incident_id, "reason": result["reason"]})
        return result

    risk_level = get_action_risk(action, policy)
    blast_radius = compute_blast_radius(action, risk_level)
    reversible = is_reversible(action)
    thresholds = policy.get("confidence_thresholds", {})
    auto_threshold = thresholds.get("auto_apply", 0.90)
    review_threshold = thresholds.get("requires_review", 0.80)

    # HIGH RISK: always require human approval regardless of confidence
    if risk_level == "high":
        result = {
            "decision": "deny_execution",
            "approval_required": True,
            "blast_radius": blast_radius,
            "reversible": reversible,
            "reason": f"High-risk action '{action}' always requires human approval",
        }
        audit_policy_decision("deny_execution", {
            "action": action, "confidence": confidence, "role": role,
            "risk_level": risk_level, "incident_id": incident_id,
            "reason": result["reason"]})
        emit_event("ai.remediation.proposed", source="policy_engine",
                   incident_id=incident_id,
                   payload={"action": action, "decision": "deny_execution",
                            "risk": risk_level, "confidence": confidence})
        return result

    # Check role authorization for risk level
    min_role = RISK_MIN_ROLE.get(risk_level, "admin")
    min_rank = ROLE_RANK.get(min_role, 3)
    user_rank = ROLE_RANK.get(role, 0)

    if user_rank < min_rank:
        result = {
            "decision": "deny_execution",
            "approval_required": True,
            "blast_radius": blast_radius,
            "reversible": reversible,
            "reason": f"Role '{role}' insufficient for {risk_level}-risk action (requires '{min_role}')",
        }
        audit_policy_decision("deny_execution", {
            "action": action, "confidence": confidence, "role": role,
            "risk_level": risk_level, "incident_id": incident_id,
            "reason": result["reason"]})
        return result

    # LOW RISK: auto-apply if confidence >= auto_apply threshold
    if risk_level == "low" and confidence >= auto_threshold:
        auto_actions = policy.get("auto_apply_actions", [])
        if action in auto_actions:
            result = {
                "decision": "auto_apply",
                "approval_required": False,
                "blast_radius": blast_radius,
                "reversible": reversible,
                "reason": f"Low-risk action '{action}' auto-approved at confidence {confidence:.2f}",
            }
            audit_policy_decision("auto_apply", {
                "action": action, "confidence": confidence, "role": role,
                "risk_level": risk_level, "incident_id": incident_id,
                "reason": result["reason"]})
            emit_event("ai.remediation.proposed", source="policy_engine",
                       incident_id=incident_id,
                       payload={"action": action, "decision": "auto_apply",
                                "risk": risk_level, "confidence": confidence})
            return result

    # MEDIUM RISK or low risk below threshold: require review
    if confidence >= review_threshold:
        result = {
            "decision": "require_review",
            "approval_required": True,
            "blast_radius": blast_radius,
            "reversible": reversible,
            "reason": f"Action '{action}' ({risk_level} risk) at confidence {confidence:.2f} requires review",
        }
        audit_policy_decision("require_review", {
            "action": action, "confidence": confidence, "role": role,
            "risk_level": risk_level, "incident_id": incident_id,
            "reason": result["reason"]})
        emit_event("ai.remediation.proposed", source="policy_engine",
                   incident_id=incident_id,
                   payload={"action": action, "decision": "require_review",
                            "risk": risk_level, "confidence": confidence})
        return result

    # Below review threshold — deny
    result = {
        "decision": "deny_execution",
        "approval_required": True,
        "blast_radius": blast_radius,
        "reversible": reversible,
        "reason": f"Confidence {confidence:.2f} below review threshold {review_threshold}",
    }
    audit_policy_decision("deny_execution", {
        "action": action, "confidence": confidence, "role": role,
        "risk_level": risk_level, "incident_id": incident_id,
        "reason": result["reason"]})
    return result


def enrich_investigation(investigation):
    """Add policy metadata to an investigation result."""
    action = investigation.get("recommended_action", "manual_review")
    confidence = investigation.get("confidence", 0)
    policy = load_policy()
    risk_level = get_action_risk(action, policy)

    investigation["blast_radius"] = compute_blast_radius(action, risk_level)
    investigation["reversible"] = is_reversible(action)
    # Re-evaluate approval based on policy engine
    evaluation = evaluate_remediation_policy(
        action, confidence, role="sre",
        incident_id=investigation.get("incident_id"))
    investigation["approval_required"] = evaluation["approval_required"]
    investigation["policy_decision"] = evaluation["decision"]
    return investigation


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "evaluate":
        action = sys.argv[2] if len(sys.argv) > 2 else "restart_service"
        confidence = float(sys.argv[3]) if len(sys.argv) > 3 else 0.85
        role = sys.argv[4] if len(sys.argv) > 4 else "sre"
        inc_id = sys.argv[5] if len(sys.argv) > 5 else None
        result = evaluate_remediation_policy(action, confidence, role, inc_id)
        print(f"[OK] Policy evaluation for '{action}'")
        print(f"     Decision: {result['decision']}")
        print(f"     Blast radius: {result['blast_radius']}")
        print(f"     Reversible: {result['reversible']}")
        print(f"     Approval required: {result['approval_required']}")
        print(f"     Reason: {result['reason']}")
    elif cmd == "risk":
        action = sys.argv[2] if len(sys.argv) > 2 else "restart_service"
        policy = load_policy()
        risk = get_action_risk(action, policy)
        print(f"  {action}: {risk}")
    else:
        print("Usage: policy_engine.py [evaluate <action> <confidence> <role> [incident_id]|risk <action>]")


if __name__ == "__main__":
    main()
