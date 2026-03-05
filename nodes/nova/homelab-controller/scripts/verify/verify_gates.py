#!/usr/bin/env python3
"""P40 — Policy Gates: enforce minimum thresholds before allowing operations."""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "verification_policy.json"
ARTIFACTS = ROOT / "artifacts" / "verification"
DASHBOARD_DATA = ROOT / "dashboard" / "static" / "data"


def load_json_safe(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def evaluate_gates():
    with open(CONFIG) as f:
        policy = json.load(f)

    gates = policy.get("policy_gates", {})
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    checks = []

    # SLO budget gate
    slo_min = gates.get("slo_budget_min_pct", 10)
    slo_data = load_json_safe(DASHBOARD_DATA / "slo_status.json")
    if slo_data and "budget_remaining_pct" in slo_data:
        budget = slo_data["budget_remaining_pct"]
        checks.append({"gate": "slo_budget", "threshold": slo_min, "actual": budget, "pass": budget >= slo_min})
    else:
        checks.append({"gate": "slo_budget", "threshold": slo_min, "actual": None, "pass": True, "note": "no SLO data"})

    # Open incidents gate
    max_incidents = gates.get("max_open_incidents", 3)
    incident_data = load_json_safe(DASHBOARD_DATA / "incident_status.json")
    if incident_data and "open_count" in incident_data:
        count = incident_data["open_count"]
        checks.append({"gate": "open_incidents", "threshold": max_incidents, "actual": count, "pass": count <= max_incidents})
    else:
        checks.append({"gate": "open_incidents", "threshold": max_incidents, "actual": 0, "pass": True, "note": "no incident data"})

    # DR readiness gate
    dr_min = gates.get("dr_readiness_min_score", 60)
    dr_data = load_json_safe(DASHBOARD_DATA / "dr_status.json")
    if dr_data and "readiness_score" in dr_data:
        score = dr_data["readiness_score"]
        checks.append({"gate": "dr_readiness", "threshold": dr_min, "actual": score, "pass": score >= dr_min})
    else:
        checks.append({"gate": "dr_readiness", "threshold": dr_min, "actual": None, "pass": True, "note": "no DR data"})

    # Security audit gate
    sec_min = gates.get("security_audit_min_score", 60)
    sec_data = load_json_safe(DASHBOARD_DATA / "sec_status.json")
    if sec_data and "audit_score" in sec_data:
        score = sec_data["audit_score"]
        checks.append({"gate": "security_audit", "threshold": sec_min, "actual": score, "pass": score >= sec_min})
    else:
        checks.append({"gate": "security_audit", "threshold": sec_min, "actual": None, "pass": True, "note": "no security data"})

    total = len(checks)
    passing = sum(1 for c in checks if c["pass"])
    all_pass = passing == total

    report = {
        "timestamp": timestamp,
        "gates": checks,
        "summary": {"total": total, "passing": passing},
        "pass": all_pass,
        "action": "ALLOW" if all_pass else "BLOCK",
    }

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    with open(ARTIFACTS / "gates_latest.json", "w") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    report = evaluate_gates()
    icon = "🟢" if report["pass"] else "🔴"
    print(f"{icon} Policy gates: {report['action']} ({report['summary']['passing']}/{report['summary']['total']})")
    for g in report["gates"]:
        gi = "✅" if g["pass"] else "❌"
        actual = g["actual"] if g["actual"] is not None else g.get("note", "?")
        print(f"  {gi} {g['gate']}: {actual} (threshold: {g['threshold']})")
