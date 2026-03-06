#!/usr/bin/env python3
"""Phase 6: Generate evidence pack and postmortem stub."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def main():
    scenario = sys.argv[1] if len(sys.argv) > 1 else "gateway_restart_outage"
    demo_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".")
    timestamp = sys.argv[3] if len(sys.argv) > 3 else datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S")

    # Load all phase outputs
    phases = {}
    for phase in ["baseline", "chaos", "detection", "remediation", "validation"]:
        f = demo_dir / f"{phase}.json"
        if f.exists():
            with open(f) as fh:
                phases[phase] = json.load(fh)

    # Evidence pack
    evidence = {
        "scenario": scenario,
        "timestamp": timestamp,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "phases": phases,
        "summary": {
            "chaos_injected": phases.get("chaos", {}).get("injected", False),
            "failure_detected": phases.get("detection", {}).get("detected", False),
            "remediation_success": phases.get("remediation", {}).get("success", False),
            "recovery_validated": phases.get("validation", {}).get("all_passed", False),
        }
    }

    with open(demo_dir / "evidence_pack.json", "w") as f:
        json.dump(evidence, f, indent=2)

    # Postmortem stub
    summary = evidence["summary"]
    postmortem = f"""# Postmortem: {scenario}
## Date: {timestamp}

## Summary
- Chaos injected: {'Yes' if summary['chaos_injected'] else 'No'}
- Failure detected: {'Yes' if summary['failure_detected'] else 'No'}
- Remediation success: {'Yes' if summary['remediation_success'] else 'No'}
- Recovery validated: {'Yes' if summary['recovery_validated'] else 'No'}

## Timeline
1. **Baseline**: System health captured
2. **Chaos**: {phases.get('chaos', {}).get('description', 'N/A')}
3. **Detection**: {phases.get('detection', {}).get('detection_method', 'N/A')} in {phases.get('detection', {}).get('time_to_detect_sec', '?')}s
4. **Remediation**: {len(phases.get('remediation', {}).get('actions', []))} actions taken in {phases.get('remediation', {}).get('duration_sec', '?')}s
5. **Validation**: {'All checks passed' if summary['recovery_validated'] else 'Some checks failed'}

## Impact
- Duration: ~{phases.get('remediation', {}).get('duration_sec', 0) + phases.get('detection', {}).get('time_to_detect_sec', 0):.1f}s total
- Affected services: {phases.get('chaos', {}).get('target', 'unknown')}
- Data loss: None (simulated)

## Root Cause
Simulated scenario for reliability demonstration.

## Action Items
- [ ] Review detection time — target < 30s
- [ ] Review remediation steps — target < 60s
- [ ] Validate monitoring coverage for this failure mode
- [ ] Update runbook if needed

## Evidence
All artifacts in: `{demo_dir}`
"""

    with open(demo_dir / "postmortem.md", "w") as f:
        f.write(postmortem)

    print(f"  Evidence pack: {demo_dir}/evidence_pack.json")
    print(f"  Postmortem:    {demo_dir}/postmortem.md")

    all_pass = all(summary.values())
    print(f"  Overall: {'PASS' if all_pass else 'PARTIAL'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
