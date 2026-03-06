#!/usr/bin/env python3
"""After-action review generator for closed incidents."""
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
REVIEW_DIR = ROOT / "data" / "self_improvement" / "reviews"
INVESTIGATION_DIR = ROOT / "data" / "incidents" / "investigations"
INCIDENTS_FILE = ROOT / "artifacts" / "recovery" / "incidents.json"

sys.path.insert(0, str(ROOT / "platform" / "events"))
from bus import emit as emit_event


def load_incident(incident_id):
    """Load incident by ID."""
    if not INCIDENTS_FILE.exists():
        return None
    with open(INCIDENTS_FILE) as f:
        data = json.load(f)
    for inc in data.get("incidents", []):
        if inc.get("incident_id") == incident_id:
            return inc
    return None


def load_investigation_for_incident(incident_id):
    """Find the latest investigation for an incident."""
    if not INVESTIGATION_DIR.exists():
        return None
    for f in sorted(INVESTIGATION_DIR.glob("INV-*.json"), reverse=True):
        inv = json.load(open(f))
        if inv.get("incident_id") == incident_id:
            return inv
    return None


def generate_review(incident_id, actual_action=None, outcome=None,
                    human_override=False, lessons=None):
    """Generate an after-action review for a closed incident."""
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc)
    review_id = f"AAR-{ts.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

    incident = load_incident(incident_id)
    investigation = load_investigation_for_incident(incident_id)

    playbook_used = investigation.get("playbook", "none") if investigation else "none"
    recommended = investigation.get("recommended_action", "manual_review") if investigation else "manual_review"
    confidence = investigation.get("confidence", 0) if investigation else 0

    if actual_action is None:
        actual_action = recommended
    if outcome is None:
        outcome = "resolved" if incident and incident.get("status") == "resolved" else "pending"
    if lessons is None:
        lessons = []
        if confidence < 0.80:
            lessons.append("Low confidence investigation — consider adding evidence sources")
        if human_override:
            lessons.append("Human override of AI recommendation — review playbook accuracy")
        if actual_action != recommended:
            lessons.append(f"Actual action '{actual_action}' differed from recommended '{recommended}'")

    # Derive proposed improvements
    improvements = []
    if actual_action != recommended:
        improvements.append({
            "type": "playbook_update",
            "description": f"Review playbook '{playbook_used}' — recommended '{recommended}' but '{actual_action}' was used",
        })
    if confidence < 0.80:
        improvements.append({
            "type": "confidence_threshold_update",
            "description": f"Confidence was {confidence:.2f} — consider adjusting evidence steps or thresholds",
        })
    if not investigation:
        improvements.append({
            "type": "documentation_update",
            "description": "No investigation found for incident — ensure investigations are triggered",
        })

    review = {
        "review_id": review_id,
        "incident_id": incident_id,
        "timestamp": ts.isoformat(),
        "playbook_used": playbook_used,
        "recommended_action": recommended,
        "actual_action": actual_action,
        "outcome": outcome,
        "human_override": human_override,
        "confidence": confidence,
        "lessons_learned": lessons,
        "proposed_improvements": improvements,
    }

    out_file = REVIEW_DIR / f"{review_id}.json"
    with open(out_file, "w") as f:
        json.dump(review, f, indent=2)

    emit_event("self_improvement.review.created", source="reviewer",
               incident_id=incident_id,
               payload={"review_id": review_id, "improvements": len(improvements)})

    print(f"[OK] Review {review_id}")
    print(f"     Incident: {incident_id}")
    print(f"     Playbook: {playbook_used}")
    print(f"     Outcome: {outcome}")
    print(f"     Improvements: {len(improvements)}")
    return review


def list_reviews():
    """List all reviews."""
    if not REVIEW_DIR.exists():
        print("  No reviews.")
        return []
    reviews = []
    for f in sorted(REVIEW_DIR.glob("AAR-*.json")):
        r = json.load(open(f))
        reviews.append(r)
        print(f"  {r['review_id']:<30} {r['incident_id']:<25} {r['outcome']:<12} {len(r['proposed_improvements'])} improvements")
    if not reviews:
        print("  No reviews.")
    return reviews


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "generate":
        inc_id = sys.argv[2] if len(sys.argv) > 2 else "INC-MANUAL"
        actual = sys.argv[3] if len(sys.argv) > 3 else None
        outcome = sys.argv[4] if len(sys.argv) > 4 else None
        override = "--override" in sys.argv
        generate_review(inc_id, actual_action=actual, outcome=outcome, human_override=override)
    elif cmd == "list":
        list_reviews()
    else:
        print("Usage: reviewer.py [generate <incident_id> [actual_action] [outcome] [--override]|list]")


if __name__ == "__main__":
    main()
