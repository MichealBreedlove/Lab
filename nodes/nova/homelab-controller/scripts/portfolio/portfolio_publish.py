#!/usr/bin/env python3
"""portfolio_publish.py — Commit and publish site to GitHub Pages."""

import json
import subprocess
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent.parent
LAB_ROOT = ROOT_DIR.parent.parent.parent
CONFIG_DIR = ROOT_DIR / "config"


def load_policy():
    with open(CONFIG_DIR / "portfolio_policy.json") as f:
        return json.load(f)


def publish():
    """Commit site changes and push."""
    policy = load_policy()
    now = datetime.now().isoformat()[:19]

    print("=== Portfolio Publish ===")

    # Commit changes
    subprocess.run(["git", "add", "-A"], cwd=str(LAB_ROOT), capture_output=True)

    diff = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=str(LAB_ROOT), capture_output=True
    )

    if diff.returncode == 0:
        print("No changes to publish.")
        return

    subprocess.run(
        ["git", "commit", "-m", f"portfolio: publish {now}", "--quiet"],
        cwd=str(LAB_ROOT), capture_output=True
    )

    result = subprocess.run(
        ["git", "push", "--quiet"],
        cwd=str(LAB_ROOT), capture_output=True, text=True
    )

    if result.returncode == 0:
        print(f"✅ Published at {now}")
        site_url = policy.get("publish_target", {}).get("site_url", "")
        if site_url:
            print(f"   Site: {site_url}")
    else:
        print(f"❌ Push failed: {result.stderr}")

    # Write status for dashboard
    status = {
        "last_publish": now,
        "success": result.returncode == 0,
        "site_url": policy.get("publish_target", {}).get("site_url", "")
    }
    status_dir = LAB_ROOT / "services" / "openclaw" / "portfolio"
    status_dir.mkdir(parents=True, exist_ok=True)
    with open(status_dir / "latest.json", "w") as f:
        json.dump(status, f, indent=2)

    print("=== Publish complete ===")


if __name__ == "__main__":
    publish()
