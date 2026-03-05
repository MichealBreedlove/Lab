#!/usr/bin/env python3
"""sli_compute.py — Transform raw events into SLIs per window.

Computes:
- availability = good / total
- success_rate = successes / total
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any

from slo_utils import load_policy


def compute_sli(events: List[Dict], window_seconds: int) -> Dict[str, Any]:
    """Compute SLI for a given time window.

    Returns:
        {
            "window_seconds": int,
            "total_events": int,
            "good_events": int,
            "bad_events": int,
            "sli_value": float (0.0 - 1.0),
            "window_start": str,
            "window_end": str,
            "sufficient_data": bool
        }
    """
    now = datetime.now()
    cutoff = now - timedelta(seconds=window_seconds)

    window_events = []
    for e in events:
        try:
            ts = datetime.fromisoformat(e["timestamp"])
            if ts >= cutoff:
                window_events.append(e)
        except (ValueError, KeyError):
            continue

    total = len(window_events)
    good = sum(1 for e in window_events if e.get("good", False))
    bad = total - good

    sli_value = good / total if total > 0 else None

    return {
        "window_seconds": window_seconds,
        "total_events": total,
        "good_events": good,
        "bad_events": bad,
        "sli_value": sli_value,
        "window_start": cutoff.isoformat(),
        "window_end": now.isoformat(),
        "sufficient_data": total >= 1
    }


def compute_all_windows(events: List[Dict]) -> Dict[str, Dict]:
    """Compute SLIs across all configured windows.

    Returns {window_name: sli_result}
    """
    policy = load_policy()
    windows = policy.get("windows", {})

    results = {}
    for name, seconds in windows.items():
        results[name] = compute_sli(events, seconds)

    return results


def compute_slis_for_catalog(all_events: Dict[str, List]) -> Dict[str, Dict]:
    """Compute SLIs for all SLOs across all windows.

    Args:
        all_events: {slo_id: [events...]}

    Returns:
        {slo_id: {window_name: sli_result}}
    """
    results = {}
    for slo_id, events in all_events.items():
        results[slo_id] = compute_all_windows(events)
    return results


if __name__ == "__main__":
    import json
    from slo_utils import load_catalog
    from sli_sources import load_all_events
    from datetime import timedelta

    catalog = load_catalog()
    since = datetime.now() - timedelta(days=28)
    all_events = load_all_events(catalog, since)
    slis = compute_slis_for_catalog(all_events)

    for slo_id, windows in slis.items():
        print(f"\n=== {slo_id} ===")
        for window_name, result in windows.items():
            sli = result["sli_value"]
            sli_str = f"{sli:.4f}" if sli is not None else "N/A"
            print(f"  {window_name}: SLI={sli_str} ({result['good_events']}/{result['total_events']})")
