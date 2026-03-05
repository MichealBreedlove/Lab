#!/usr/bin/env python3
"""slo_runner.py — Main entry point for SLO pipeline.

Runs: evaluate → render reports → publish
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# Add slo/ to path
sys.path.insert(0, str(Path(__file__).parent / "slo"))

from slo_utils import load_policy, load_state, save_state, today_str, week_str
from slo_eval import run_and_persist
from slo_render import save_daily_report, save_weekly_report
from slo_publish import publish


def main():
    policy = load_policy()

    if not policy.get("enabled", True):
        print("SLO pipeline disabled in policy. Exiting.")
        return

    mode = policy.get("mode", "supervised")
    print(f"=== SLO Runner — mode: {mode} ===")

    # Step 1: Evaluate
    print("\n[1/3] Evaluating SLOs...")
    result = run_and_persist()

    s = result["summary"]
    print(f"  {s['total_slos']} SLOs evaluated")
    print(f"  ✅ {s['slos_meeting_objective']} OK | "
          f"⚠️ {s['slos_at_risk']} at risk | "
          f"🔴 {s['slos_exhausted']} exhausted")

    # Step 2: Render reports
    print("\n[2/3] Rendering reports...")
    daily_dir = save_daily_report(result)
    print(f"  Daily report: {daily_dir}")

    # Check if we should do weekly report
    state = load_state()
    schedule = policy.get("schedule", {})
    weekly_day = schedule.get("weekly_day", "monday").lower()
    today_weekday = datetime.now().strftime("%A").lower()

    if today_weekday == weekly_day:
        current_week = week_str()
        if state.get("last_weekly_report") != current_week:
            weekly_dir = save_weekly_report(result)
            state["last_weekly_report"] = current_week
            save_state(state)
            print(f"  Weekly report: {weekly_dir}")
        else:
            print(f"  Weekly report already generated for {current_week}")
    else:
        print(f"  Weekly report: skipped (runs on {weekly_day})")

    # Step 3: Publish
    print("\n[3/3] Publishing...")
    if mode == "dry_run":
        print("  Dry run — skipping publish")
    else:
        publish(result)

    # Update state
    state = load_state()
    state["last_daily_report"] = today_str()
    save_state(state)

    print("\n=== SLO Runner complete ===")

    # Exit with non-zero if any SLO is exhausted
    if s["slos_exhausted"] > 0:
        sys.exit(2)
    elif s["slos_at_risk"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
