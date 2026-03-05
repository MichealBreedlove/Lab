#!/usr/bin/env python3
"""budget.py — Compute error budgets for SLOs.

Computes:
- Allowed bad events for the budget period (28d default)
- Consumed budget (bad-to-date)
- Remaining budget %
- Budget "at risk" flags
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List

from slo_utils import load_catalog


def compute_budget(
    slo: dict,
    events: List[Dict],
    budget_window_days: int = 28
) -> Dict[str, Any]:
    """Compute error budget for a single SLO.

    Returns:
        {
            "slo_id": str,
            "objective": float,
            "budget_window_days": int,
            "total_events": int,
            "good_events": int,
            "bad_events": int,
            "allowed_bad_events": float,
            "consumed_budget_pct": float,
            "remaining_budget_pct": float,
            "budget_at_risk": bool,
            "budget_exhausted": bool,
            "sli_current": float or None
        }
    """
    now = datetime.now()
    cutoff = now - timedelta(days=budget_window_days)

    # Filter events to budget window
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

    objective = slo.get("objective", 0.99)
    error_rate_allowed = 1.0 - objective

    # Allowed bad events = total * error_rate_allowed
    allowed_bad = total * error_rate_allowed if total > 0 else 0

    # Budget consumption
    if allowed_bad > 0:
        consumed_pct = (bad / allowed_bad) * 100
    elif bad > 0:
        consumed_pct = 100.0  # any bad event = budget blown
    else:
        consumed_pct = 0.0

    remaining_pct = max(0.0, 100.0 - consumed_pct)
    sli_current = good / total if total > 0 else None

    return {
        "slo_id": slo["id"],
        "objective": objective,
        "budget_window_days": budget_window_days,
        "total_events": total,
        "good_events": good,
        "bad_events": bad,
        "allowed_bad_events": round(allowed_bad, 2),
        "consumed_budget_pct": round(consumed_pct, 2),
        "remaining_budget_pct": round(remaining_pct, 2),
        "budget_at_risk": remaining_pct < 30.0,
        "budget_exhausted": remaining_pct <= 0.0,
        "sli_current": round(sli_current, 6) if sli_current is not None else None
    }


def compute_all_budgets(
    catalog: dict,
    all_events: Dict[str, List],
    budget_window_days: int = 28
) -> Dict[str, Dict]:
    """Compute error budgets for all SLOs.

    Returns {slo_id: budget_result}
    """
    results = {}
    for slo in catalog.get("slos", []):
        events = all_events.get(slo["id"], [])
        results[slo["id"]] = compute_budget(slo, events, budget_window_days)
    return results


if __name__ == "__main__":
    from sli_sources import load_all_events

    catalog = load_catalog()
    since = datetime.now() - timedelta(days=28)
    all_events = load_all_events(catalog, since)
    budgets = compute_all_budgets(catalog, all_events)

    for slo_id, b in budgets.items():
        status = "🔴 EXHAUSTED" if b["budget_exhausted"] else \
                 "🟡 AT RISK" if b["budget_at_risk"] else "🟢 OK"
        print(f"{slo_id}: {status} — {b['remaining_budget_pct']}% remaining "
              f"({b['bad_events']}/{b['allowed_bad_events']:.0f} bad events used)")
