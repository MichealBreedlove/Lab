#!/usr/bin/env python3
"""burn_rate.py — Compute burn rates and multi-window alerts.

Burn rate = (observed error rate in window) / (target error rate)
A burn rate of 1.0 means consuming budget at exactly the allowed pace.
>1 means burning faster than sustainable.
"""

from typing import Dict, Any, List

from slo_utils import load_policy


def compute_burn_rate(
    sli_value: float,
    objective: float
) -> float:
    """Compute burn rate from SLI and objective.

    burn_rate = (1 - sli_value) / (1 - objective)
    """
    error_budget_rate = 1.0 - objective
    if error_budget_rate <= 0:
        return 0.0

    observed_error_rate = 1.0 - sli_value if sli_value is not None else 1.0
    return observed_error_rate / error_budget_rate


def compute_burn_rates_for_slo(
    slo: dict,
    sli_windows: Dict[str, Dict]
) -> Dict[str, Any]:
    """Compute burn rates across all windows for a single SLO.

    Returns:
        {
            "slo_id": str,
            "objective": float,
            "windows": {
                window_name: {
                    "sli_value": float,
                    "burn_rate": float,
                    "total_events": int,
                    "sufficient_data": bool
                }
            },
            "alerts": [...]
        }
    """
    objective = slo.get("objective", 0.99)
    policy = load_policy()
    thresholds = policy.get("burn_thresholds", {})

    windows = {}
    for window_name, sli_result in sli_windows.items():
        sli_value = sli_result.get("sli_value")
        burn = compute_burn_rate(sli_value, objective) if sli_value is not None else None

        windows[window_name] = {
            "sli_value": sli_value,
            "burn_rate": round(burn, 3) if burn is not None else None,
            "total_events": sli_result.get("total_events", 0),
            "sufficient_data": sli_result.get("sufficient_data", False)
        }

    # Check alert thresholds
    alerts = []
    for severity, config in thresholds.items():
        window = config.get("window", "rolling_1h")
        multiplier = config.get("multiplier", 1)
        w = windows.get(window, {})
        burn = w.get("burn_rate")

        if burn is not None and w.get("sufficient_data") and burn >= multiplier:
            alerts.append({
                "severity": severity,
                "window": window,
                "burn_rate": burn,
                "threshold": multiplier,
                "message": f"{severity.upper()}: burn rate {burn:.1f}x in {window} "
                           f"(threshold: {multiplier}x)"
            })

    return {
        "slo_id": slo["id"],
        "objective": objective,
        "windows": windows,
        "alerts": alerts
    }


def compute_all_burn_rates(
    catalog: dict,
    all_slis: Dict[str, Dict]
) -> Dict[str, Dict]:
    """Compute burn rates for all SLOs.

    Args:
        all_slis: {slo_id: {window_name: sli_result}}

    Returns {slo_id: burn_rate_result}
    """
    results = {}
    for slo in catalog.get("slos", []):
        sli_windows = all_slis.get(slo["id"], {})
        results[slo["id"]] = compute_burn_rates_for_slo(slo, sli_windows)
    return results


if __name__ == "__main__":
    from datetime import datetime, timedelta
    from slo_utils import load_catalog
    from sli_sources import load_all_events
    from sli_compute import compute_slis_for_catalog

    catalog = load_catalog()
    since = datetime.now() - timedelta(days=28)
    all_events = load_all_events(catalog, since)
    all_slis = compute_slis_for_catalog(all_events)
    burn_rates = compute_all_burn_rates(catalog, all_slis)

    for slo_id, br in burn_rates.items():
        print(f"\n=== {slo_id} ===")
        for wname, w in br["windows"].items():
            burn = w["burn_rate"]
            burn_str = f"{burn:.2f}x" if burn is not None else "N/A"
            print(f"  {wname}: burn={burn_str}")
        if br["alerts"]:
            for a in br["alerts"]:
                print(f"  ⚠️  {a['message']}")
