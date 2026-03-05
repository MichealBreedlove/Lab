#!/usr/bin/env python3
"""P40 — Verification Status Publisher."""

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts" / "verification"
DASHBOARD_DATA = ROOT / "dashboard" / "static" / "data"


def load_json_safe(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def publish():
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    synthetic = load_json_safe(ARTIFACTS / "synthetic_latest.json")
    canary = load_json_safe(ARTIFACTS / "canary_latest.json")
    gates = load_json_safe(ARTIFACTS / "gates_latest.json")

    syn_pass = synthetic.get("pass", False) if synthetic else False
    can_pass = canary.get("pass", False) if canary else False
    gate_pass = gates.get("pass", False) if gates else False

    all_pass = syn_pass and can_pass and gate_pass
    status = "GREEN" if all_pass else "YELLOW" if (syn_pass or can_pass) else "RED"

    result = {
        "timestamp": timestamp,
        "status": status,
        "synthetic": {"pass": syn_pass, "summary": synthetic.get("summary") if synthetic else None},
        "canary": {"pass": can_pass, "summary": canary.get("summary") if canary else None},
        "gates": {"pass": gate_pass, "action": gates.get("action") if gates else None},
    }

    DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)
    with open(DASHBOARD_DATA / "verify_status.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


if __name__ == "__main__":
    r = publish()
    icon = "🟢" if r["status"] == "GREEN" else "🟡" if r["status"] == "YELLOW" else "🔴"
    print(f"{icon} Verification: {r['status']}")
