#!/usr/bin/env python3
"""P39 — Portfolio Badges: generate markdown status badges from subsystem data."""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_DATA = ROOT / "dashboard" / "static" / "data"
META_DIR = ROOT.parents[2] / "_meta"


def load_json_safe(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def badge_md(label, value, color):
    """Generate a simple markdown badge (no external service needed)."""
    return f"![{label}](https://img.shields.io/badge/{label.replace(' ', '_')}-{value.replace(' ', '_')}-{color})"


def generate_badges():
    badges = []

    # Observability
    obs = load_json_safe(DASHBOARD_DATA / "obs_status.json")
    if obs:
        s = obs.get("status", "unknown")
        c = "brightgreen" if s == "GREEN" else "yellow" if s == "YELLOW" else "red"
        badges.append(badge_md("Observability", s, c))

    # Infrastructure
    infra = load_json_safe(DASHBOARD_DATA / "infra_status.json")
    if infra:
        s = infra.get("status", "unknown")
        c = "brightgreen" if s == "GREEN" else "yellow" if s == "YELLOW" else "red"
        badges.append(badge_md("Infrastructure", s, c))

    # Security
    sec = load_json_safe(DASHBOARD_DATA / "sec_status.json")
    if sec:
        score = sec.get("audit_score", 0)
        c = "brightgreen" if score >= 80 else "yellow" if score >= 60 else "red"
        badges.append(badge_md("Security", f"{score}%25", c))

    # Portfolio
    port = load_json_safe(DASHBOARD_DATA / "portfolio_status.json")
    if port:
        n = port.get("docs_count", 0)
        c = "brightgreen" if n >= 3 else "yellow" if n > 0 else "red"
        badges.append(badge_md("Portfolio Docs", str(n), c))

    # Static badges
    badges.append(badge_md("Nodes", "4", "blue"))
    badges.append(badge_md("Subsystems", "10+", "blue"))
    badges.append(badge_md("Language", "Python_3", "3776AB"))

    return badges


def write_badges(lab_path=None):
    lab = Path(lab_path) if lab_path else ROOT.parents[2]
    meta = lab / "_meta"
    meta.mkdir(parents=True, exist_ok=True)

    badges = generate_badges()
    content = "<!-- Auto-generated badges -->\n" + " ".join(badges) + "\n"
    (meta / "BADGES.md").write_text(content)

    return {"badges": len(badges), "output": str(meta / "BADGES.md")}


if __name__ == "__main__":
    result = write_badges()
    print(f"🏷️  Generated {result['badges']} badges → {result['output']}")
