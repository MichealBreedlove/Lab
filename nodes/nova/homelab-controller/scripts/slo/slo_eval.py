#!/usr/bin/env python3
"""slo_eval.py — Unified SLO evaluation: SLIs + budgets + burn rates + alerts.

This is the main orchestrator that ties together sli_sources, sli_compute,
budget, and burn_rate into a single evaluation pass.
"""

from datetime import datetime, timedelta
from typing import Dict, Any

from slo_utils import (
    load_catalog, load_policy, load_state, save_state,
    now_iso, today_str, ARTIFACTS_DIR, save_json, append_jsonl
)
from sli_sources import load_all_events
from sli_compute import compute_slis_for_catalog
from budget import compute_all_budgets
from burn_rate import compute_all_burn_rates


def evaluate_all() -> Dict[str, Any]:
    """Run full SLO evaluation.

    Returns the complete evaluation result with SLIs, budgets, burn rates, and alerts.
    """
    catalog = load_catalog()
    policy = load_policy()

    # Load events for 28-day window
    since = datetime.now() - timedelta(days=28)
    all_events = load_all_events(catalog, since)

    # Compute SLIs
    all_slis = compute_slis_for_catalog(all_events)

    # Compute budgets
    budgets = compute_all_budgets(catalog, all_events)

    # Compute burn rates
    burn_rates = compute_all_burn_rates(catalog, all_slis)

    # Collect all alerts
    all_alerts = []
    for slo_id, br in burn_rates.items():
        all_alerts.extend(br.get("alerts", []))

    # Check gating conditions
    gating = policy.get("gating_integration", {})
    gate_decisions = []

    for slo_id, b in budgets.items():
        # Check budget-based tier cap
        cap_config = gating.get("cap_max_action_tier_on_burn", {})
        if b["remaining_budget_pct"] < cap_config.get("budget_below_pct", 50):
            gate_decisions.append({
                "slo_id": slo_id,
                "action": "cap_tier",
                "max_tier": cap_config.get("max_tier", 1),
                "reason": f"Budget at {b['remaining_budget_pct']}% "
                          f"(threshold: {cap_config.get('budget_below_pct', 50)}%)"
            })

    # Build result
    result = {
        "timestamp": now_iso(),
        "slos": {},
        "alerts": all_alerts,
        "gate_decisions": gate_decisions,
        "summary": {
            "total_slos": len(catalog.get("slos", [])),
            "slos_meeting_objective": 0,
            "slos_at_risk": 0,
            "slos_exhausted": 0,
            "active_alerts": len(all_alerts)
        }
    }

    for slo in catalog.get("slos", []):
        slo_id = slo["id"]
        budget = budgets.get(slo_id, {})

        # Count summary stats
        if budget.get("budget_exhausted"):
            result["summary"]["slos_exhausted"] += 1
        elif budget.get("budget_at_risk"):
            result["summary"]["slos_at_risk"] += 1
        else:
            result["summary"]["slos_meeting_objective"] += 1

        result["slos"][slo_id] = {
            "name": slo.get("name", slo_id),
            "objective": slo.get("objective"),
            "slis": all_slis.get(slo_id, {}),
            "budget": budget,
            "burn_rates": burn_rates.get(slo_id, {}).get("windows", {}),
            "alerts": burn_rates.get(slo_id, {}).get("alerts", [])
        }

    return result


def run_and_persist() -> Dict[str, Any]:
    """Run evaluation, save current state, and append to history."""
    result = evaluate_all()

    # Save current snapshot
    save_json(ARTIFACTS_DIR / "current.json", result)

    # Append to history
    append_jsonl(ARTIFACTS_DIR / "history.jsonl", {
        "timestamp": result["timestamp"],
        "summary": result["summary"],
        "alerts": result["alerts"],
        "gate_decisions": result["gate_decisions"]
    })

    # Update state
    state = load_state()
    state["last_run"] = result["timestamp"]
    save_state(state)

    return result


if __name__ == "__main__":
    import json
    result = run_and_persist()

    print(f"=== SLO Evaluation @ {result['timestamp']} ===")
    s = result["summary"]
    print(f"SLOs: {s['total_slos']} total | "
          f"✅ {s['slos_meeting_objective']} OK | "
          f"⚠️  {s['slos_at_risk']} at risk | "
          f"🔴 {s['slos_exhausted']} exhausted")
    print(f"Active alerts: {s['active_alerts']}")

    for slo_id, slo_data in result["slos"].items():
        budget = slo_data.get("budget", {})
        status = "🔴" if budget.get("budget_exhausted") else \
                 "🟡" if budget.get("budget_at_risk") else "🟢"
        remaining = budget.get("remaining_budget_pct", "N/A")
        print(f"\n  {status} {slo_data['name']}: budget {remaining}% remaining")

    if result["gate_decisions"]:
        print("\n--- Gate Decisions ---")
        for g in result["gate_decisions"]:
            print(f"  🚫 {g['slo_id']}: {g['action']} (max tier {g['max_tier']}) — {g['reason']}")
