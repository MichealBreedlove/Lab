#!/usr/bin/env python3
"""sli_sources.py — Load raw signals from snapshots, actions, chaos, gateway health.

Returns normalized "events" (timestamped good/bad counts) for SLI computation.
"""

import glob
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any

from slo_utils import ROOT_DIR, load_policy, load_json


def _find_snapshot_files(artifact_root: str, since: datetime = None) -> List[Path]:
    """Find snapshot JSON files, optionally filtered by date."""
    root = ROOT_DIR / artifact_root
    if not root.exists():
        return []
    files = sorted(root.glob("**/*.json"))
    if since:
        files = [f for f in files if _file_date(f) >= since]
    return files


def _file_date(path: Path) -> datetime:
    """Extract date from file path or mtime."""
    # Try to parse YYYY-MM-DD from filename
    name = path.stem
    for part in name.split("-"):
        pass
    try:
        # Common pattern: snapshot-2026-03-04.json
        date_str = "-".join(name.split("-")[-3:])
        return datetime.strptime(date_str, "%Y-%m-%d")
    except (ValueError, IndexError):
        return datetime.fromtimestamp(path.stat().st_mtime)


def _evaluate_condition(data: dict, field: str, operator: str, value) -> bool:
    """Evaluate a condition against nested dict data."""
    parts = field.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return False
        if current is None:
            return False

    if operator == "eq":
        return current == value
    elif operator == "gte":
        return float(current) >= float(value)
    elif operator == "lte":
        return float(current) <= float(value)
    elif operator == "gt":
        return float(current) > float(value)
    elif operator == "lt":
        return float(current) < float(value)
    return False


def load_events_for_slo(slo: dict, since: datetime = None) -> List[Dict[str, Any]]:
    """Load raw events for a given SLO definition.

    Returns list of {"timestamp": ..., "good": bool, "source_file": ...}
    """
    policy = load_policy()
    source = slo["source"]
    artifact_root = policy.get("artifact_roots", {}).get(source, f"artifacts/{source}")

    events = []
    files = _find_snapshot_files(artifact_root, since)

    for fpath in files:
        try:
            data = load_json(fpath)
        except (json.JSONDecodeError, FileNotFoundError):
            continue

        good = _evaluate_condition(
            data,
            slo["good_event"]["field"],
            slo["good_event"]["operator"],
            slo["good_event"]["value"]
        )

        events.append({
            "timestamp": _file_date(fpath).isoformat(),
            "good": good,
            "source_file": str(fpath)
        })

    return events


def load_all_events(catalog: dict, since: datetime = None) -> Dict[str, List]:
    """Load events for all SLOs in catalog.

    Returns {slo_id: [events...]}
    """
    result = {}
    for slo in catalog.get("slos", []):
        result[slo["id"]] = load_events_for_slo(slo, since)
    return result


if __name__ == "__main__":
    from slo_utils import load_catalog
    catalog = load_catalog()
    since = datetime.now() - timedelta(days=28)
    all_events = load_all_events(catalog, since)
    for slo_id, events in all_events.items():
        good = sum(1 for e in events if e["good"])
        total = len(events)
        print(f"{slo_id}: {good}/{total} good events")
