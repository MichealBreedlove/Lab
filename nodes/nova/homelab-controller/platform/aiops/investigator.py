#!/usr/bin/env python3
"""AI investigation engine — deterministic playbook runner with structured output."""
import json
import socket
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

ROOT = Path(__file__).resolve().parent.parent.parent
PLAYBOOK_DIR = ROOT / "platform" / "incidents" / "playbooks"
INVESTIGATION_DIR = ROOT / "data" / "incidents" / "investigations"
POLICY_FILE = ROOT / "config" / "aiops_policy.json"

sys.path.insert(0, str(ROOT / "platform" / "events"))
from bus import emit as emit_event


def load_policy():
    if POLICY_FILE.exists():
        with open(POLICY_FILE) as f:
            return json.load(f)
    return {"enabled": True, "approval_required_below_confidence": 0.80}


def load_playbooks():
    """Load all playbook definitions."""
    playbooks = {}
    if PLAYBOOK_DIR.exists():
        for f in PLAYBOOK_DIR.glob("*.json"):
            with open(f) as fh:
                pb = json.load(fh)
                playbooks[pb["name"]] = pb
    return playbooks


def select_playbook(service, state="confirmed"):
    """Select matching playbook for a service/state."""
    playbooks = load_playbooks()
    for name, pb in playbooks.items():
        trigger = pb.get("trigger_conditions", {})
        if trigger.get("service") == service:
            valid_states = trigger.get("state", [])
            if state in valid_states:
                return pb
    return None


def gather_evidence(playbook, service, host="127.0.0.1", simulate=False):
    """Gather evidence per playbook steps. Returns list of evidence dicts."""
    evidence = []
    for step in playbook.get("evidence_steps", []):
        if step == "health_check":
            if simulate:
                evidence.append({"type": "health_check", "result": "failed", "simulated": True})
            else:
                registry_file = ROOT / "platform" / "recovery" / "health_registry.json"
                url = None
                if registry_file.exists():
                    reg = json.load(open(registry_file))
                    for svc in reg.get("services", []):
                        if svc["name"] == service:
                            url = svc.get("health_url")
                            break
                if url:
                    try:
                        resp = urlopen(url, timeout=5)
                        evidence.append({"type": "health_check", "result": "ok", "status": resp.status})
                    except Exception:
                        evidence.append({"type": "health_check", "result": "failed"})
                else:
                    evidence.append({"type": "health_check", "result": "no_url"})

        elif step == "service_status":
            if simulate:
                evidence.append({"type": "service_status", "result": "inactive", "simulated": True})
            else:
                import subprocess
                r = subprocess.run(["systemctl", "--user", "is-active", f"homelab-platform-api"],
                                   capture_output=True, text=True, timeout=5)
                status = r.stdout.strip()
                evidence.append({"type": "service_status", "result": status})

        elif step == "recent_audit_entries":
            audit_file = ROOT / "artifacts" / "identity" / "api_audit.jsonl"
            entries = []
            if audit_file.exists():
                with open(audit_file) as f:
                    lines = f.readlines()[-5:]
                    for line in lines:
                        try:
                            entries.append(json.loads(line.strip()))
                        except Exception:
                            pass
            evidence.append({"type": "audit_context", "result": f"{len(entries)} recent entries",
                             "entries": entries})

        elif step == "ping_check":
            if simulate:
                evidence.append({"type": "ping_check", "result": "failed", "simulated": True})
            else:
                try:
                    s = socket.socket()
                    s.settimeout(3)
                    s.connect((host, 22))
                    s.close()
                    evidence.append({"type": "ping_check", "result": "ok"})
                except Exception:
                    evidence.append({"type": "ping_check", "result": "failed"})

        elif step in ("ssh_check", "prometheus_target_status", "drift_report",
                       "recent_changes", "config_diff"):
            evidence.append({"type": step, "result": "simulated" if simulate else "not_implemented",
                             "simulated": simulate})

    return evidence


def compute_confidence(playbook, evidence):
    """Compute confidence score from evidence against playbook rules."""
    rules = playbook.get("confidence_rules", {})
    signals = set()
    for e in evidence:
        if e["result"] in ("failed", "inactive", "down"):
            signals.add(f"{e['type']}_{e['result']}")
        elif e["result"] == "failed":
            signals.add(f"{e['type']}_failed")

    # Check high confidence
    high_signals = set(rules.get("high", []))
    if high_signals and high_signals.issubset(signals):
        return 0.95, "high"

    # Check medium
    med_signals = set(rules.get("medium", []))
    if med_signals and med_signals.issubset(signals):
        return 0.70, "medium"

    # Low if we have any failure signals
    if signals:
        return 0.50, "low"

    return 0.10, "none"


def investigate(incident_id, service, state="confirmed", simulate=False):
    """Run a full investigation. Returns investigation dict."""
    INVESTIGATION_DIR.mkdir(parents=True, exist_ok=True)
    policy = load_policy()
    ts = datetime.now(timezone.utc)

    inv_id = f"INV-{ts.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

    # Emit start event
    emit_event("ai.investigation.started", source="investigator",
               incident_id=incident_id, payload={"investigation_id": inv_id, "service": service})

    # Select playbook
    playbook = select_playbook(service, state)
    if not playbook:
        # No matching playbook — generic investigation
        playbook = {"name": "generic", "evidence_steps": ["health_check"],
                    "confidence_rules": {"medium": ["health_check_failed"]},
                    "recommended_actions": ["restart_service"]}

    # Gather evidence
    evidence = gather_evidence(playbook, service, simulate=simulate)

    # Compute confidence
    score, level = compute_confidence(playbook, evidence)

    # Determine recommendation
    actions = playbook.get("recommended_actions", [])
    recommended = actions[0] if actions else "manual_review"

    # Build hypothesis
    failed = [e for e in evidence if e.get("result") in ("failed", "inactive", "down")]
    if failed:
        hypothesis = f"{service} service failure detected via {', '.join(e['type'] for e in failed)}"
    else:
        hypothesis = f"{service} investigation completed with no clear failure signal"

    # Risk assessment via policy engine
    risk = "low" if score >= 0.80 else "medium" if score >= 0.50 else "high"
    approval_threshold = policy.get("approval_required_below_confidence", 0.80)
    approval_required = score < approval_threshold

    investigation = {
        "investigation_id": inv_id,
        "incident_id": incident_id,
        "playbook": playbook["name"],
        "timestamp": ts.isoformat(),
        "evidence": evidence,
        "hypothesis": hypothesis,
        "confidence": score,
        "confidence_level": level,
        "recommended_action": recommended,
        "risk": risk,
        "approval_required": approval_required,
    }

    # Enrich with policy engine metadata
    try:
        from policy_engine import enrich_investigation
        investigation = enrich_investigation(investigation)
    except ImportError:
        pass

    # Persist
    out_file = INVESTIGATION_DIR / f"{inv_id}.json"
    with open(out_file, "w") as f:
        json.dump(investigation, f, indent=2)

    # Emit completion event
    emit_event("ai.investigation.completed", source="investigator",
               incident_id=incident_id,
               payload={"investigation_id": inv_id, "confidence": score,
                        "recommended_action": recommended})

    print(f"[OK] Investigation {inv_id}")
    print(f"     Playbook: {playbook['name']}")
    print(f"     Confidence: {score:.2f} ({level})")
    print(f"     Recommended: {recommended}")
    print(f"     Approval required: {approval_required}")

    return investigation


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "run":
        inc_id = sys.argv[2] if len(sys.argv) > 2 else "INC-MANUAL"
        service = sys.argv[3] if len(sys.argv) > 3 else "api"
        state = sys.argv[4] if len(sys.argv) > 4 else "confirmed"
        simulate = "--simulate" in sys.argv
        investigate(inc_id, service, state, simulate=simulate)
    elif cmd == "list":
        if INVESTIGATION_DIR.exists():
            for f in sorted(INVESTIGATION_DIR.glob("INV-*.json")):
                with open(f) as fh:
                    inv = json.load(fh)
                print(f"  {inv['investigation_id']:<30} {inv['playbook']:<18} {inv['confidence']:.2f}  {inv['recommended_action']}")
        else:
            print("  No investigations.")
    else:
        print("Usage: investigator.py [run <incident_id> <service> [state] [--simulate]|list]")


if __name__ == "__main__":
    main()
