#!/usr/bin/env python3
"""slo_gate.py — SLO-based gating for P25 Gatekeeper integration.

Provides functions that the gatekeeper can call to check if an action
should be denied or tier-capped based on current SLO state.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from slo_utils import ARTIFACTS_DIR, load_policy


def load_current_slo() -> Optional[Dict]:
    """Load the latest SLO evaluation result."""
    current = ARTIFACTS_DIR / "current.json"
    if not current.exists():
        return None
    with open(current) as f:
        return json.load(f)


def check_slo_gate(action_tier: int = 0) -> Tuple[str, str, Optional[int]]:
    """Check SLO gates for an action.

    Args:
        action_tier: The tier of the proposed action (0=safe, higher=riskier)

    Returns:
        (decision, reason, max_allowed_tier)
        decision: "ALLOW", "DENY", or "CAP"
        reason: human-readable explanation
        max_allowed_tier: if CAP, the maximum tier allowed; else None
    """
    data = load_current_slo()
    if data is None:
        return ("ALLOW", "No SLO data available — allowing by default", None)

    policy = load_policy()
    gating = policy.get("gating_integration", {})

    # Check 1: Burn rate denial
    deny_config = gating.get("deny_if_burn_rate_ge", {})
    for slo_id, slo_data in data.get("slos", {}).items():
        burn_rates = slo_data.get("burn_rates", {})

        # Check fast burn (1h window)
        fast_threshold = deny_config.get("fast_1h", 6)
        r1h = burn_rates.get("rolling_1h", {})
        if r1h.get("burn_rate") is not None and r1h["burn_rate"] >= fast_threshold:
            if r1h.get("sufficient_data"):
                return (
                    "DENY",
                    f"SLO '{slo_data.get('name', slo_id)}' burn rate {r1h['burn_rate']:.1f}x "
                    f"in 1h window (threshold: {fast_threshold}x)",
                    None
                )

        # Check slow burn (6h window)
        slow_threshold = deny_config.get("slow_6h", 2)
        r6h = burn_rates.get("rolling_6h", {})
        if r6h.get("burn_rate") is not None and r6h["burn_rate"] >= slow_threshold:
            if r6h.get("sufficient_data"):
                return (
                    "DENY",
                    f"SLO '{slo_data.get('name', slo_id)}' burn rate {r6h['burn_rate']:.1f}x "
                    f"in 6h window (threshold: {slow_threshold}x)",
                    None
                )

    # Check 2: Budget-based tier cap
    cap_config = gating.get("cap_max_action_tier_on_burn", {})
    budget_threshold = cap_config.get("budget_below_pct", 50)
    max_tier = cap_config.get("max_tier", 1)

    for slo_id, slo_data in data.get("slos", {}).items():
        budget = slo_data.get("budget", {})
        remaining = budget.get("remaining_budget_pct", 100)

        if remaining < budget_threshold:
            if action_tier > max_tier:
                return (
                    "CAP",
                    f"SLO '{slo_data.get('name', slo_id)}' budget at {remaining:.1f}% "
                    f"(threshold: {budget_threshold}%). Action tier {action_tier} exceeds "
                    f"max allowed tier {max_tier}",
                    max_tier
                )

    return ("ALLOW", "All SLO gates passed", None)


def get_slo_summary() -> Dict[str, Any]:
    """Get a compact SLO summary for gatekeeper context."""
    data = load_current_slo()
    if data is None:
        return {"available": False}

    summary = data.get("summary", {})
    slo_states = {}

    for slo_id, slo_data in data.get("slos", {}).items():
        budget = slo_data.get("budget", {})
        slo_states[slo_id] = {
            "name": slo_data.get("name", slo_id),
            "remaining_budget_pct": budget.get("remaining_budget_pct"),
            "budget_at_risk": budget.get("budget_at_risk", False),
            "budget_exhausted": budget.get("budget_exhausted", False),
            "active_alerts": len(slo_data.get("alerts", []))
        }

    return {
        "available": True,
        "timestamp": data.get("timestamp"),
        "summary": summary,
        "slo_states": slo_states
    }


if __name__ == "__main__":
    import sys

    tier = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    decision, reason, max_tier = check_slo_gate(tier)

    icon = {"ALLOW": "✅", "DENY": "🚫", "CAP": "⚠️"}.get(decision, "?")
    print(f"{icon} {decision}: {reason}")
    if max_tier is not None:
        print(f"   Max allowed tier: {max_tier}")
