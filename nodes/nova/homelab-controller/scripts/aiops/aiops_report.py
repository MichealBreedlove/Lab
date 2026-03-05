#!/usr/bin/env python3
"""P34 — AIOps Weekly Report: generate comprehensive operations report."""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "artifacts" / "aiops"
CAPACITY_DIR = ROOT / "artifacts" / "capacity"
DR_DIR = ROOT / "artifacts" / "dr"
DOCS_DIR = ROOT / "docs" / "generated"


def load_json_safe(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def generate_report():
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    date_str = time.strftime("%Y-%m-%d")

    capacity = load_json_safe(CAPACITY_DIR / "latest.json")
    forecast = load_json_safe(CAPACITY_DIR / "forecast.json")
    recommendations = load_json_safe(CAPACITY_DIR / "recommendations.json")
    dr = load_json_safe(DR_DIR / "dr_status.json")
    anomalies = load_json_safe(ARTIFACTS_DIR / "anomalies.json")
    correlations = load_json_safe(ARTIFACTS_DIR / "correlations.json")
    analysis = load_json_safe(ARTIFACTS_DIR / "analysis.json")

    lines = [
        f"# Operations Report — {date_str}",
        "",
        f"*Generated: {timestamp}*",
        "",
        "## Executive Summary",
        "",
    ]

    # DR status
    if dr:
        dr_icon = "🟢" if dr.get("status") == "GREEN" else "🟡" if dr.get("status") == "YELLOW" else "🔴"
        lines.append(f"- **DR Readiness:** {dr_icon} {dr.get('status')} (score: {dr.get('readiness_score')})")
    else:
        lines.append("- **DR Readiness:** No data")

    # Capacity status
    if capacity:
        alert_count = len(capacity.get("alerts", []))
        cap_icon = "🟢" if alert_count == 0 else "🟡" if alert_count < 3 else "🔴"
        lines.append(f"- **Capacity:** {cap_icon} {alert_count} alerts")
    else:
        lines.append("- **Capacity:** No data")

    # Anomalies
    anom_count = len(anomalies.get("anomalies", [])) if anomalies else 0
    lines.append(f"- **Anomalies:** {'✅ None' if anom_count == 0 else f'⚠️ {anom_count} detected'}")

    # Incidents
    inc_count = correlations.get("incident_count", 0) if correlations else 0
    lines.append(f"- **Correlated Incidents:** {'✅ None' if inc_count == 0 else f'🔴 {inc_count}'}")

    lines.append("")

    # Node details
    if capacity:
        lines.extend(["## Node Health", "", "| Node | CPU | Memory | Disk | Load | Status |", "|------|-----|--------|------|------|--------|"])
        for name, data in capacity.get("nodes", {}).items():
            if data.get("status") == "skipped":
                lines.append(f"| {name} | — | — | — | — | ⏭️ Windows |")
                continue
            status = "🟢" if not data.get("alerts") else "🟡"
            lines.append(f"| {name} | {data.get('cpu_pct', '?')}% | {data.get('memory_pct', '?')}% | {data.get('disk_pct', '?')}% | {data.get('load_ratio', '?')}x | {status} |")
        lines.append("")

    # Forecasts
    if forecast and forecast.get("forecasts"):
        lines.extend(["## Capacity Forecasts", ""])
        for node, fc in forecast["forecasts"].items():
            for metric, data in fc.items():
                days = data.get("days_until_full")
                if days is not None:
                    icon = "🔴" if data["status"] == "critical" else "🟡" if data["status"] == "warning" else "🟢"
                    lines.append(f"- {icon} {node}/{metric}: **{days}d** until full")
        lines.append("")

    # Recommendations
    if recommendations and recommendations.get("recommendations"):
        lines.extend(["## Recommendations", ""])
        for r in recommendations["recommendations"]:
            icon = "🚨" if r["priority"] == "high" else "⚠️" if r["priority"] == "medium" else "💡"
            lines.append(f"- {icon} **{r['action']}**: {r['reason']}")
            if r.get("suggestion"):
                lines.append(f"  - → {r['suggestion']}")
        lines.append("")

    # AI Analysis
    if analysis and analysis.get("analysis"):
        lines.extend(["## AI Analysis", "", analysis["analysis"], ""])

    # Write report
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    report_text = "\n".join(lines)
    (ARTIFACTS_DIR / f"report_{date_str}.md").write_text(report_text)
    (ARTIFACTS_DIR / "report_latest.md").write_text(report_text)

    return {
        "file": f"artifacts/aiops/report_{date_str}.md",
        "sections": ["summary", "nodes", "forecasts", "recommendations", "analysis"],
        "timestamp": timestamp,
    }


def main():
    parser = argparse.ArgumentParser(description="AIOps Weekly Report")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = generate_report()

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"📊 Report generated: {result['file']}")

    sys.exit(0)


if __name__ == "__main__":
    main()
