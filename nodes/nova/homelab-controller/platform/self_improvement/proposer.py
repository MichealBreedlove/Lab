#!/usr/bin/env python3
"""Improvement proposal generator — converts reviews into actionable proposals."""
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
REVIEW_DIR = ROOT / "data" / "self_improvement" / "reviews"
PROPOSAL_DIR = ROOT / "data" / "self_improvement" / "proposals"

sys.path.insert(0, str(ROOT / "platform" / "events"))
from bus import emit as emit_event

VALID_TYPES = [
    "documentation_update",
    "artifact_template_update",
    "playbook_update",
    "confidence_threshold_update",
    "alert_mapping_update",
    "policy_change_request",
]


def load_review(review_id):
    """Load a review by ID."""
    f = REVIEW_DIR / f"{review_id}.json"
    if f.exists():
        return json.load(open(f))
    return None


def generate_proposals_from_review(review_id):
    """Convert a review's proposed improvements into formal proposals."""
    PROPOSAL_DIR.mkdir(parents=True, exist_ok=True)
    review = load_review(review_id)
    if not review:
        print(f"[ERROR] Review {review_id} not found")
        return []

    proposals = []
    ts = datetime.now(timezone.utc)

    for imp in review.get("proposed_improvements", []):
        prop_type = imp.get("type", "documentation_update")
        if prop_type not in VALID_TYPES:
            prop_type = "documentation_update"

        prop_id = f"PROP-{ts.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        proposal = {
            "proposal_id": prop_id,
            "review_id": review_id,
            "incident_id": review.get("incident_id"),
            "type": prop_type,
            "description": imp.get("description", ""),
            "status": "pending",
            "created_at": ts.isoformat(),
            "source": "after_action_review",
            "risk_level": _assess_risk(prop_type),
            "validation_required": prop_type not in ("documentation_update", "artifact_template_update"),
        }

        out_file = PROPOSAL_DIR / f"{prop_id}.json"
        with open(out_file, "w") as f:
            json.dump(proposal, f, indent=2)

        emit_event("self_improvement.proposal.created", source="proposer",
                   incident_id=review.get("incident_id"),
                   payload={"proposal_id": prop_id, "type": prop_type})

        proposals.append(proposal)
        print(f"[OK] Proposal {prop_id} ({prop_type})")

    return proposals


def _assess_risk(prop_type):
    """Assess risk level of a proposal type."""
    low_risk = {"documentation_update", "artifact_template_update"}
    medium_risk = {"playbook_update", "confidence_threshold_update", "alert_mapping_update"}
    if prop_type in low_risk:
        return "low"
    if prop_type in medium_risk:
        return "medium"
    return "high"


def list_proposals(status=None):
    """List proposals with optional status filter."""
    if not PROPOSAL_DIR.exists():
        print("  No proposals.")
        return []
    proposals = []
    for f in sorted(PROPOSAL_DIR.glob("PROP-*.json")):
        p = json.load(open(f))
        if status and p.get("status") != status:
            continue
        proposals.append(p)
        print(f"  {p['proposal_id']:<30} {p['type']:<30} {p['status']:<10} {p['risk_level']}")
    if not proposals:
        print("  No proposals.")
    return proposals


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "generate":
        review_id = sys.argv[2] if len(sys.argv) > 2 else None
        if not review_id:
            print("Usage: proposer.py generate <review_id>")
            return
        generate_proposals_from_review(review_id)
    elif cmd == "list":
        status = sys.argv[2] if len(sys.argv) > 2 else None
        list_proposals(status)
    else:
        print("Usage: proposer.py [generate <review_id>|list [status]]")


if __name__ == "__main__":
    main()
