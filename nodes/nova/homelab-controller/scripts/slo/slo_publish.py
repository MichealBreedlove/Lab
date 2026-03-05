#!/usr/bin/env python3
"""slo_publish.py — Publish SLO reports to dashboard + optional Telegram.

Reads the latest evaluation from current.json and publishes to configured targets.
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, Any

from slo_utils import load_policy, ARTIFACTS_DIR, load_json, now_iso, append_jsonl
from slo_render import render_short_summary


def publish_to_dashboard(result: Dict[str, Any]) -> bool:
    """Copy SLO data to dashboard static directory for web rendering.

    The dashboard reads current.json from a known path.
    """
    # Dashboard expects data at a known location
    dashboard_dir = Path(__file__).parent.parent.parent / "dashboard" / "static" / "data"
    dashboard_dir.mkdir(parents=True, exist_ok=True)

    target = dashboard_dir / "slo_current.json"
    with open(target, "w") as f:
        json.dump(result, f, indent=2, default=str)

    return True


def publish_to_telegram(result: Dict[str, Any], channel_id: str) -> bool:
    """Send short summary to Telegram via OpenClaw or curl.

    This is a placeholder — adapt to your actual Telegram delivery method.
    """
    summary = render_short_summary(result)

    # Try openclaw message send if available
    try:
        subprocess.run(
            ["openclaw", "message", "send", "--channel", "telegram",
             "--target", channel_id, "--message", summary],
            capture_output=True, text=True, timeout=30
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    print(f"Telegram publish skipped (no delivery method available)")
    print(f"Message would be:\n{summary}")
    return False


def publish(result: Dict[str, Any]):
    """Publish to all configured targets."""
    policy = load_policy()
    publish_config = policy.get("publish", {})

    log_entries = []

    # Dashboard
    if publish_config.get("dashboard", True):
        ok = publish_to_dashboard(result)
        log_entries.append({
            "target": "dashboard",
            "success": ok,
            "timestamp": now_iso()
        })
        print(f"Dashboard: {'✅' if ok else '❌'}")

    # Telegram
    tg = publish_config.get("telegram", {})
    if tg.get("enabled") and tg.get("channel_id"):
        ok = publish_to_telegram(result, tg["channel_id"])
        log_entries.append({
            "target": "telegram",
            "success": ok,
            "timestamp": now_iso()
        })
        print(f"Telegram: {'✅' if ok else '❌'}")

    # Log publish results
    for entry in log_entries:
        append_jsonl(ARTIFACTS_DIR / "publish_log.jsonl", entry)


if __name__ == "__main__":
    current_file = ARTIFACTS_DIR / "current.json"
    if current_file.exists():
        result = load_json(current_file)
        publish(result)
    else:
        print("No current.json found. Run slo_eval.py first.")
