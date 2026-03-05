#!/usr/bin/env python3
"""P38 — Security Status Publisher: generate sec_status.json for dashboard."""

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "artifacts" / "security"
DASHBOARD_DATA = ROOT / "dashboard" / "static" / "data"


def load_json_safe(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def publish():
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    audit = load_json_safe(ARTIFACTS_DIR / "sec_audit_latest.json")
    scan = load_json_safe(ARTIFACTS_DIR / "secretscan_latest.json")

    scores = []
    if audit:
        for name, data in audit.get("nodes", {}).items():
            if data.get("summary"):
                scores.append(data["summary"]["score"])

    avg_score = round(sum(scores) / len(scores)) if scores else 0
    scan_clean = scan.get("pass", False) if scan else False

    status = "GREEN" if avg_score >= 80 and scan_clean else "YELLOW" if avg_score >= 60 else "RED"

    result = {
        "timestamp": timestamp,
        "status": status,
        "audit_score": avg_score,
        "scan_clean": scan_clean,
        "scan_violations": scan.get("violation_count", 0) if scan else 0,
        "last_audit": audit.get("timestamp") if audit else None,
        "last_scan": scan.get("timestamp") if scan else None,
    }

    DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)
    with open(DASHBOARD_DATA / "sec_status.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


if __name__ == "__main__":
    r = publish()
    icon = "🟢" if r["status"] == "GREEN" else "🟡" if r["status"] == "YELLOW" else "🔴"
    print(f"{icon} Security: {r['status']} (audit: {r['audit_score']}%, scan: {'✅' if r['scan_clean'] else '❌'})")
