#!/usr/bin/env python3
"""Promotion policy engine + safe auto-promotion for validated proposals."""
import json
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PROPOSAL_DIR = ROOT / "data" / "self_improvement" / "proposals"
VALIDATION_DIR = ROOT / "data" / "self_improvement" / "validations"
PROMOTED_DIR = ROOT / "data" / "self_improvement" / "promoted"
POLICY_FILE = ROOT / "config" / "self_improvement_policy.json"

sys.path.insert(0, str(ROOT / "platform" / "events"))
from bus import emit as emit_event


def load_policy():
    """Load self-improvement promotion policy."""
    if POLICY_FILE.exists():
        with open(POLICY_FILE) as f:
            return json.load(f)
    return {
        "enabled": True,
        "auto_promote_types": ["documentation_update", "artifact_template_update"],
        "require_review_types": ["playbook_update", "confidence_threshold_update", "alert_mapping_update"],
        "deny_types": ["policy_change_request"],
    }


def load_proposal(proposal_id):
    f = PROPOSAL_DIR / f"{proposal_id}.json"
    if f.exists():
        return json.load(open(f))
    return None


def find_validation(proposal_id):
    """Find latest validation for a proposal."""
    if not VALIDATION_DIR.exists():
        return None
    for f in sorted(VALIDATION_DIR.glob("VAL-*.json"), reverse=True):
        v = json.load(open(f))
        if v.get("proposal_id") == proposal_id:
            return v
    return None


def evaluate_promotion(proposal_id):
    """Evaluate whether a proposal can be promoted.

    Returns: "auto_promote" | "require_review" | "deny"
    """
    policy = load_policy()
    proposal = load_proposal(proposal_id)
    if not proposal:
        return "deny", "Proposal not found"

    if not policy.get("enabled", True):
        return "deny", "Self-improvement policy disabled"

    prop_type = proposal.get("type", "")

    # Check deny list first
    if prop_type in policy.get("deny_types", []):
        return "deny", f"Type '{prop_type}' is in deny list"

    # Check validation requirement
    if policy.get("require_validation", True):
        validation = find_validation(proposal_id)
        if not validation:
            return "deny", "No validation found — run validator first"
        if validation.get("result") != "passed":
            return "deny", f"Validation failed: {validation.get('result')}"

    # Check proposal status
    if proposal.get("status") not in ("validated", "pending"):
        return "deny", f"Proposal status '{proposal.get('status')}' not promotable"

    # Auto-promote safe types
    if prop_type in policy.get("auto_promote_types", []):
        return "auto_promote", f"Type '{prop_type}' is auto-promotable"

    # Require review for medium-risk types
    if prop_type in policy.get("require_review_types", []):
        return "require_review", f"Type '{prop_type}' requires human review"

    # Default to require_review for unknown types
    return "require_review", f"Unknown type '{prop_type}' defaults to review"


def promote_proposal(proposal_id, force=False):
    """Promote a validated proposal to the promoted artifacts store."""
    PROMOTED_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc)

    decision, reason = evaluate_promotion(proposal_id)

    if decision == "deny" and not force:
        print(f"[DENIED] {proposal_id}: {reason}")
        return {"decision": decision, "reason": reason, "promoted": False}

    if decision == "require_review" and not force:
        print(f"[REVIEW] {proposal_id}: {reason}")
        return {"decision": decision, "reason": reason, "promoted": False}

    # Promote
    proposal = load_proposal(proposal_id)
    if not proposal:
        return {"decision": "deny", "reason": "Proposal not found", "promoted": False}

    promotion_id = f"PROM-{ts.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    promoted = {
        "promotion_id": promotion_id,
        "proposal_id": proposal_id,
        "type": proposal.get("type"),
        "description": proposal.get("description"),
        "promoted_at": ts.isoformat(),
        "decision": decision,
        "reason": reason,
        "forced": force and decision != "auto_promote",
    }

    out_file = PROMOTED_DIR / f"{promotion_id}.json"
    with open(out_file, "w") as f:
        json.dump(promoted, f, indent=2)

    # Update proposal status
    proposal["status"] = "promoted"
    proposal["promotion_id"] = promotion_id
    with open(PROPOSAL_DIR / f"{proposal_id}.json", "w") as f:
        json.dump(proposal, f, indent=2)

    emit_event("self_improvement.promotion.applied", source="promotion_engine",
               payload={"promotion_id": promotion_id, "proposal_id": proposal_id,
                        "type": proposal.get("type"), "forced": promoted["forced"]})

    print(f"[OK] Promoted {proposal_id} -> {promotion_id}")
    print(f"     Type: {proposal.get('type')}")
    print(f"     Decision: {decision}")
    return {"decision": decision, "reason": reason, "promoted": True,
            "promotion_id": promotion_id}


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "evaluate":
        prop_id = sys.argv[2] if len(sys.argv) > 2 else None
        if not prop_id:
            print("Usage: promotion.py evaluate <proposal_id>")
            return
        decision, reason = evaluate_promotion(prop_id)
        print(f"  Decision: {decision}")
        print(f"  Reason: {reason}")
    elif cmd == "promote":
        prop_id = sys.argv[2] if len(sys.argv) > 2 else None
        force = "--force" in sys.argv
        if not prop_id:
            print("Usage: promotion.py promote <proposal_id> [--force]")
            return
        promote_proposal(prop_id, force=force)
    elif cmd == "list":
        if PROMOTED_DIR.exists():
            for f in sorted(PROMOTED_DIR.glob("PROM-*.json")):
                p = json.load(open(f))
                print(f"  {p['promotion_id']:<30} {p['proposal_id']:<30} {p.get('type','?')}")
        else:
            print("  No promotions.")
    else:
        print("Usage: promotion.py [evaluate|promote|list] <proposal_id> [--force]")


if __name__ == "__main__":
    main()
