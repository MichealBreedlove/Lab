#!/usr/bin/env python3
"""Generate a unique change ID and metadata record."""
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CHANGES_DIR = ROOT / "changes"

VALID_TRIGGERS = [
    "proxmox_config", "opnsense_backup", "switch_config",
    "remediation", "chaos_experiment", "dr_drill",
    "drift_detection", "manual", "controlplane_tick",
]


def create_change(trigger="manual", summary="", details=None, author="nova"):
    """Create a new change record. Returns change_id and path."""
    ts = datetime.now(timezone.utc)
    change_id = f"CHG-{ts.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

    change_dir = CHANGES_DIR / change_id
    change_dir.mkdir(parents=True, exist_ok=True)
    (change_dir / "evidence").mkdir(exist_ok=True)

    record = {
        "change_id": change_id,
        "created_at": ts.isoformat(),
        "trigger": trigger if trigger in VALID_TRIGGERS else "manual",
        "summary": summary or f"Change triggered by {trigger}",
        "author": author,
        "status": "open",
        "details": details or {},
        "phases": {
            "created": ts.isoformat(),
            "diffed": None,
            "validated": None,
            "rendered": None,
            "published": None,
        },
    }

    with open(change_dir / "change.json", "w") as f:
        json.dump(record, f, indent=2)

    print(f"[OK] Change created: {change_id}")
    print(f"     Path: {change_dir}")
    return change_id, change_dir


def main():
    trigger = sys.argv[1] if len(sys.argv) > 1 else "manual"
    summary = sys.argv[2] if len(sys.argv) > 2 else ""
    change_id, _ = create_change(trigger=trigger, summary=summary)
    print(change_id)
    return 0


if __name__ == "__main__":
    sys.exit(main())
