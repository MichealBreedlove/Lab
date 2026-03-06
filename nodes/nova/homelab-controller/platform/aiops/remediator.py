#!/usr/bin/env python3
"""Remediation artifact generator — produces Git-friendly incident artifacts."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
REMEDIATION_DIR = ROOT / "data" / "remediation" / "incidents"
INVESTIGATION_DIR = ROOT / "data" / "incidents" / "investigations"

sys.path.insert(0, str(ROOT / "platform" / "events"))
from bus import emit as emit_event


def load_investigation(investigation_id=None, incident_id=None):
    """Load an investigation by ID or find latest for an incident."""
    if not INVESTIGATION_DIR.exists():
        return None
    if investigation_id:
        f = INVESTIGATION_DIR / f"{investigation_id}.json"
        if f.exists():
            return json.load(open(f))
    if incident_id:
        for f in sorted(INVESTIGATION_DIR.glob("INV-*.json"), reverse=True):
            inv = json.load(open(f))
            if inv.get("incident_id") == incident_id:
                return inv
    # Return latest
    files = sorted(INVESTIGATION_DIR.glob("INV-*.json"))
    if files:
        return json.load(open(files[-1]))
    return None


def generate_summary_md(inv):
    """Generate incident summary markdown."""
    evidence_lines = []
    for e in inv.get("evidence", []):
        evidence_lines.append(f"- {e['type']}: {e['result']}")

    return f"""# Incident {inv['incident_id']}

## Overview
- Service: {inv.get('playbook', 'unknown').replace('_', ' ')}
- Investigation: {inv['investigation_id']}
- Playbook: {inv['playbook']}
- Timestamp: {inv['timestamp']}

## Evidence
{chr(10).join(evidence_lines) or '- No evidence collected'}

## Hypothesis
{inv.get('hypothesis', 'No hypothesis generated')}

## Recommended Action
{inv.get('recommended_action', 'manual_review')}

## Confidence
{inv.get('confidence', 0):.2f} ({inv.get('confidence_level', 'unknown')})

## Risk
{inv.get('risk', 'unknown')}

## Approval Required
{'Yes' if inv.get('approval_required') else 'No'}

## Rollback Notes
Re-apply previous known-good configuration if recommended action fails.
Verify service health after any remediation step.
"""


def generate_proposal_json(inv):
    """Generate remediation proposal JSON."""
    return {
        "incident_id": inv["incident_id"],
        "investigation_id": inv["investigation_id"],
        "recommended_action": inv.get("recommended_action", "manual_review"),
        "confidence": inv.get("confidence", 0),
        "risk": inv.get("risk", "unknown"),
        "approval_required": inv.get("approval_required", True),
        "rollback_notes": "Restore previous known-good configuration.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def generate_patch_plan_md(inv):
    """Generate patch plan markdown."""
    action = inv.get("recommended_action", "manual_review")
    return f"""# Patch Plan: {inv['incident_id']}

## Action
{action}

## Pre-Conditions
- Verify current service state
- Confirm backup exists
- Review evidence from investigation {inv['investigation_id']}

## Steps
1. Execute: `{action}`
2. Wait 30 seconds for service stabilization
3. Run health check
4. Verify via dashboard/monitoring

## Rollback
- If step 3 fails: restore previous config
- If rollback fails: escalate to human operator

## Verification
- Health endpoint returns 200
- No new incidents within 10 minutes
- Audit log confirms successful action

## Sign-Off
- Confidence: {inv.get('confidence', 0):.2f}
- Risk: {inv.get('risk', 'unknown')}
- Auto-approved: {'Yes' if not inv.get('approval_required') else 'No — requires human approval'}
"""


def generate_artifacts(incident_id=None, investigation_id=None, include_patch_plan=True):
    """Generate all remediation artifacts for an investigation."""
    REMEDIATION_DIR.mkdir(parents=True, exist_ok=True)

    inv = load_investigation(investigation_id=investigation_id, incident_id=incident_id)
    if not inv:
        print("[ERROR] No investigation found")
        return None

    inc_id = inv["incident_id"]
    prefix = REMEDIATION_DIR / inc_id

    # Summary markdown
    summary_path = Path(f"{prefix}-summary.md")
    with open(summary_path, "w") as f:
        f.write(generate_summary_md(inv))

    # Proposal JSON
    proposal_path = Path(f"{prefix}-proposal.json")
    proposal = generate_proposal_json(inv)
    with open(proposal_path, "w") as f:
        json.dump(proposal, f, indent=2)

    # Patch plan
    patch_path = None
    if include_patch_plan:
        patch_path = Path(f"{prefix}-patch-plan.md")
        with open(patch_path, "w") as f:
            f.write(generate_patch_plan_md(inv))

    # Emit event
    emit_event("ai.remediation.artifact_created", source="remediator",
               incident_id=inc_id,
               payload={
                   "investigation_id": inv["investigation_id"],
                   "files": [str(summary_path.name), str(proposal_path.name)]
                            + ([str(patch_path.name)] if patch_path else []),
               })

    print(f"[OK] Remediation artifacts generated for {inc_id}")
    print(f"     Summary: {summary_path.name}")
    print(f"     Proposal: {proposal_path.name}")
    if patch_path:
        print(f"     Patch plan: {patch_path.name}")

    return {
        "incident_id": inc_id,
        "summary": str(summary_path),
        "proposal": str(proposal_path),
        "patch_plan": str(patch_path) if patch_path else None,
    }


def git_branch_suggestion(incident_id):
    """Suggest git branch name and commit message."""
    return {
        "branch": f"incident/{incident_id}-remediation",
        "commit_message": f"docs(incident): add remediation artifacts for {incident_id}",
    }


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "generate":
        inc_id = sys.argv[2] if len(sys.argv) > 2 else None
        inv_id = sys.argv[3] if len(sys.argv) > 3 else None
        patch = "--no-patch" not in sys.argv
        result = generate_artifacts(incident_id=inc_id, investigation_id=inv_id,
                                    include_patch_plan=patch)
        if result:
            git = git_branch_suggestion(result["incident_id"])
            print(f"     Git branch: {git['branch']}")
            print(f"     Commit msg: {git['commit_message']}")
    elif cmd == "list":
        if REMEDIATION_DIR.exists():
            for f in sorted(REMEDIATION_DIR.glob("*-summary.md")):
                print(f"  {f.stem}")
        else:
            print("  No remediation artifacts.")
    else:
        print("Usage: remediator.py [generate <incident_id> [investigation_id] [--no-patch]|list]")


if __name__ == "__main__":
    main()
