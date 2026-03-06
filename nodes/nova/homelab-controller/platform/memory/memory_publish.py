#!/usr/bin/env python3
"""Publish memory status to dashboard data file."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DASHBOARD_DATA = ROOT / "dashboard" / "static" / "data"

sys.path.insert(0, str(ROOT / "platform" / "memory"))
from store import memory_stats
from graph import relation_stats
from lifecycle import memory_hygiene_report


def publish():
    """Export memory status to dashboard JSON."""
    DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)

    ms = memory_stats()
    rs = relation_stats()
    hygiene = memory_hygiene_report()

    status = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_entries": ms.get("total", 0),
        "active": ms.get("active", 0),
        "archived": ms.get("archived", 0),
        "by_category": ms.get("by_category", {}),
        "relation_count": rs.get("total", 0),
        "relations_by_type": rs.get("by_type", {}),
        "stale_candidates": hygiene.get("stale_candidates", 0),
        "policy_enabled": hygiene.get("policy_enabled", True),
        "memory_aware_routing": True,
        "memory_aware_investigation": True,
    }

    out_file = DASHBOARD_DATA / "memory_status.json"
    with open(out_file, "w") as f:
        json.dump(status, f, indent=2)

    print(f"[OK] Memory status published to {out_file.name}")
    return status


if __name__ == "__main__":
    publish()
