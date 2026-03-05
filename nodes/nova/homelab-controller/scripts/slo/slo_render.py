#!/usr/bin/env python3
"""slo_render.py — Render SLO reports from evaluation results.

Generates:
- Markdown daily/weekly reports
- Short text summaries (for Telegram)
- JSON data files
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from slo_utils import (
    ARTIFACTS_DIR, load_json, save_json, today_str, week_str
)


def render_markdown_report(result: Dict[str, Any]) -> str:
    """Render a full markdown SLO report."""
    lines = []
    lines.append(f"# SLO Report — {today_str()}")
    lines.append(f"\nGenerated: {result.get('timestamp', 'N/A')}\n")

    s = result.get("summary", {})
    lines.append("## Summary")
    lines.append(f"- **Total SLOs:** {s.get('total_slos', 0)}")
    lines.append(f"- **Meeting objective:** {s.get('slos_meeting_objective', 0)} ✅")
    lines.append(f"- **At risk:** {s.get('slos_at_risk', 0)} ⚠️")
    lines.append(f"- **Budget exhausted:** {s.get('slos_exhausted', 0)} 🔴")
    lines.append(f"- **Active alerts:** {s.get('active_alerts', 0)}")
    lines.append("")

    lines.append("## SLO Details\n")
    for slo_id, slo_data in result.get("slos", {}).items():
        budget = slo_data.get("budget", {})
        status = "🔴" if budget.get("budget_exhausted") else \
                 "🟡" if budget.get("budget_at_risk") else "🟢"

        lines.append(f"### {status} {slo_data.get('name', slo_id)}")
        lines.append(f"- **Objective:** {slo_data.get('objective', 'N/A')}")
        lines.append(f"- **Current SLI:** {budget.get('sli_current', 'N/A')}")
        lines.append(f"- **Budget remaining:** {budget.get('remaining_budget_pct', 'N/A')}%")
        lines.append(f"- **Bad events:** {budget.get('bad_events', 0)} / "
                     f"{budget.get('allowed_bad_events', 0)} allowed")

        # Burn rates
        burn_rates = slo_data.get("burn_rates", {})
        if burn_rates:
            lines.append("- **Burn rates:**")
            for wname, w in burn_rates.items():
                burn = w.get("burn_rate")
                burn_str = f"{burn:.2f}x" if burn is not None else "N/A"
                lines.append(f"  - {wname}: {burn_str}")

        # Alerts
        alerts = slo_data.get("alerts", [])
        if alerts:
            lines.append("- **Alerts:**")
            for a in alerts:
                lines.append(f"  - ⚠️ {a.get('message', '')}")

        lines.append("")

    # Gate decisions
    gate_decisions = result.get("gate_decisions", [])
    if gate_decisions:
        lines.append("## Gate Decisions\n")
        for g in gate_decisions:
            lines.append(f"- 🚫 **{g['slo_id']}**: {g['action']} "
                        f"(max tier {g.get('max_tier', 'N/A')}) — {g.get('reason', '')}")
        lines.append("")

    return "\n".join(lines)


def render_short_summary(result: Dict[str, Any]) -> str:
    """Render a short text summary (for Telegram, <25 lines)."""
    lines = []
    s = result.get("summary", {})
    lines.append(f"📊 SLO Report — {today_str()}")
    lines.append(f"✅ {s.get('slos_meeting_objective', 0)} OK | "
                 f"⚠️ {s.get('slos_at_risk', 0)} risk | "
                 f"🔴 {s.get('slos_exhausted', 0)} exhausted")

    for slo_id, slo_data in result.get("slos", {}).items():
        budget = slo_data.get("budget", {})
        status = "🔴" if budget.get("budget_exhausted") else \
                 "🟡" if budget.get("budget_at_risk") else "🟢"
        remaining = budget.get("remaining_budget_pct", "?")
        lines.append(f"  {status} {slo_data.get('name', slo_id)}: {remaining}%")

    alerts = result.get("alerts", [])
    if alerts:
        lines.append(f"\n🚨 {len(alerts)} alert(s)")
        for a in alerts[:5]:
            lines.append(f"  {a.get('message', '')}")

    return "\n".join(lines)


def save_daily_report(result: Dict[str, Any]):
    """Save daily report files."""
    date = today_str()
    report_dir = ARTIFACTS_DIR / "reports" / "daily" / date
    report_dir.mkdir(parents=True, exist_ok=True)

    # Markdown
    md = render_markdown_report(result)
    (report_dir / "slo_report.md").write_text(md)

    # Short text
    txt = render_short_summary(result)
    (report_dir / "slo_report.txt").write_text(txt)

    # JSON
    save_json(report_dir / "slo_report.json", result)

    return report_dir


def save_weekly_report(result: Dict[str, Any]):
    """Save weekly report files."""
    week = week_str()
    report_dir = ARTIFACTS_DIR / "reports" / "weekly" / week
    report_dir.mkdir(parents=True, exist_ok=True)

    md = render_markdown_report(result)
    (report_dir / "slo_report.md").write_text(md)

    txt = render_short_summary(result)
    (report_dir / "slo_report.txt").write_text(txt)

    save_json(report_dir / "slo_report.json", result)

    return report_dir


if __name__ == "__main__":
    current_file = ARTIFACTS_DIR / "current.json"
    if current_file.exists():
        result = load_json(current_file)
        print(render_markdown_report(result))
    else:
        print("No current.json found. Run slo_eval.py first.")
