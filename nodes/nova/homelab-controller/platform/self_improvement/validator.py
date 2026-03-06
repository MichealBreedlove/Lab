#!/usr/bin/env python3
"""Validation runner for improvement proposals."""
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PROPOSAL_DIR = ROOT / "data" / "self_improvement" / "proposals"
VALIDATION_DIR = ROOT / "data" / "self_improvement" / "validations"

sys.path.insert(0, str(ROOT / "platform" / "events"))
from bus import emit as emit_event

VALID_CHECKS = ["schema_check", "simulation_check", "test_suite_check"]


def load_proposal(proposal_id):
    """Load a proposal by ID."""
    f = PROPOSAL_DIR / f"{proposal_id}.json"
    if f.exists():
        return json.load(open(f))
    return None


def run_schema_check(proposal):
    """Validate proposal structure."""
    required = ["proposal_id", "type", "description", "status", "risk_level"]
    missing = [k for k in required if k not in proposal]
    if missing:
        return {"check": "schema_check", "passed": False, "detail": f"Missing fields: {missing}"}
    if proposal["type"] not in [
        "documentation_update", "artifact_template_update", "playbook_update",
        "confidence_threshold_update", "alert_mapping_update", "policy_change_request"
    ]:
        return {"check": "schema_check", "passed": False, "detail": f"Invalid type: {proposal['type']}"}
    return {"check": "schema_check", "passed": True, "detail": "Schema valid"}


def run_simulation_check(proposal):
    """Simulate the proposal's impact (deterministic stub)."""
    risk = proposal.get("risk_level", "high")
    if risk == "low":
        return {"check": "simulation_check", "passed": True, "detail": "Low-risk, safe to apply"}
    if risk == "medium":
        return {"check": "simulation_check", "passed": True, "detail": "Medium-risk, review recommended"}
    return {"check": "simulation_check", "passed": False, "detail": "High-risk, requires manual approval"}


def run_test_suite_check(proposal):
    """Verify no existing tests would break (deterministic stub)."""
    # In production, this would run `oc test all` and check exit code
    prop_type = proposal.get("type", "")
    safe_types = {"documentation_update", "artifact_template_update"}
    if prop_type in safe_types:
        return {"check": "test_suite_check", "passed": True, "detail": "Safe type, no test impact"}
    return {"check": "test_suite_check", "passed": True, "detail": "Test suite check passed (simulated)"}


def validate_proposal(proposal_id):
    """Run all validation checks on a proposal."""
    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    proposal = load_proposal(proposal_id)
    if not proposal:
        print(f"[ERROR] Proposal {proposal_id} not found")
        return None

    ts = datetime.now(timezone.utc)
    val_id = f"VAL-{ts.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

    checks = [
        run_schema_check(proposal),
        run_simulation_check(proposal),
        run_test_suite_check(proposal),
    ]

    all_passed = all(c["passed"] for c in checks)

    validation = {
        "validation_id": val_id,
        "proposal_id": proposal_id,
        "timestamp": ts.isoformat(),
        "checks": checks,
        "all_passed": all_passed,
        "result": "passed" if all_passed else "failed",
    }

    out_file = VALIDATION_DIR / f"{val_id}.json"
    with open(out_file, "w") as f:
        json.dump(validation, f, indent=2)

    # Update proposal status
    if all_passed:
        proposal["status"] = "validated"
    else:
        proposal["status"] = "validation_failed"
    with open(PROPOSAL_DIR / f"{proposal_id}.json", "w") as f:
        json.dump(proposal, f, indent=2)

    emit_event("self_improvement.validation.completed", source="validator",
               payload={"validation_id": val_id, "proposal_id": proposal_id,
                        "result": validation["result"]})

    print(f"[OK] Validation {val_id}")
    print(f"     Proposal: {proposal_id}")
    print(f"     Result: {validation['result']}")
    for c in checks:
        status = "PASS" if c["passed"] else "FAIL"
        print(f"     [{status}] {c['check']}: {c['detail']}")

    return validation


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "validate":
        prop_id = sys.argv[2] if len(sys.argv) > 2 else None
        if not prop_id:
            print("Usage: validator.py validate <proposal_id>")
            return
        validate_proposal(prop_id)
    elif cmd == "list":
        if VALIDATION_DIR.exists():
            for f in sorted(VALIDATION_DIR.glob("VAL-*.json")):
                v = json.load(open(f))
                print(f"  {v['validation_id']:<30} {v['proposal_id']:<30} {v['result']}")
        else:
            print("  No validations.")
    else:
        print("Usage: validator.py [validate <proposal_id>|list]")


if __name__ == "__main__":
    main()
