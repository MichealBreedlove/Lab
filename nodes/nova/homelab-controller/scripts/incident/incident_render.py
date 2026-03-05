#!/usr/bin/env python3
"""incident_render.py — Render incident reports and postmortems as markdown."""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from incident_state import (
    load_incident, list_incidents, ARTIFACTS_DIR,
    ROOT_DIR
)

DOCS_DIR = ROOT_DIR / "docs" / "incidents"


def render_incident_md(incident: Dict[str, Any]) -> str:
    """Render incident status page as markdown."""
    inc = incident
    status_icon = {"open": "🔴", "resolved": "✅", "mitigated": "🟡"}.get(
        inc.get("status"), "❓")

    lines = [
        f"# {status_icon} Incident: {inc['id']}",
        "",
        f"**Title:** {inc.get('title', 'Untitled')}",
        f"**Severity:** {inc.get('severity', '?')}",
        f"**Status:** {inc.get('status', '?')}",
        f"**Trigger:** {inc.get('trigger', '?')}",
        f"**Opened:** {inc.get('opened_at', '?')}",
    ]

    if inc.get("resolved_at"):
        lines.append(f"**Resolved:** {inc['resolved_at']}")
    if inc.get("slo_id"):
        lines.append(f"**SLO:** {inc['slo_id']}")
    if inc.get("description"):
        lines.append(f"\n**Description:** {inc['description']}")

    # Blast radius
    if inc.get("blast_radius"):
        lines.append(f"\n**Blast Radius:** {', '.join(inc['blast_radius'])}")
    if inc.get("spof_tags"):
        lines.append(f"**SPOF Tags:** {', '.join(inc['spof_tags'])}")

    # Timeline
    lines.append("\n## Timeline\n")
    for event in inc.get("timeline", []):
        ts = event.get("timestamp", "?")[:19]
        ev = event.get("event", "?")
        detail = event.get("detail", "")
        actor = event.get("actor", "")
        lines.append(f"- **[{ts}]** `{ev}` — {detail} _{actor}_")

    # Evidence
    if inc.get("evidence_paths"):
        lines.append("\n## Evidence\n")
        for p in inc["evidence_paths"]:
            lines.append(f"- `{p}`")

    # Actions taken
    if inc.get("actions_taken"):
        lines.append("\n## Actions Taken\n")
        for a in inc["actions_taken"]:
            lines.append(f"- {a}")

    # Resolution
    if inc.get("resolution_summary"):
        lines.append(f"\n## Resolution\n\n{inc['resolution_summary']}")

    return "\n".join(lines)


def render_timeline_md(incident: Dict[str, Any]) -> str:
    """Render just the timeline as markdown."""
    inc = incident
    lines = [
        f"# Timeline: {inc['id']} — {inc.get('title', '')}",
        f"\nSeverity: {inc.get('severity')} | Status: {inc.get('status')}",
        ""
    ]

    for event in inc.get("timeline", []):
        ts = event.get("timestamp", "?")[:19]
        ev = event.get("event", "?")
        detail = event.get("detail", "")
        actor = event.get("actor", "")
        lines.append(f"| {ts} | {ev} | {detail} | {actor} |")

    return "\n".join(lines)


def render_postmortem_md(incident: Dict[str, Any]) -> str:
    """Render a recruiter-grade postmortem from an incident."""
    inc = incident
    duration = ""
    if inc.get("opened_at") and inc.get("resolved_at"):
        try:
            opened = datetime.fromisoformat(inc["opened_at"])
            resolved = datetime.fromisoformat(inc["resolved_at"])
            delta = resolved - opened
            hours = delta.total_seconds() / 3600
            duration = f"{hours:.1f} hours"
        except (ValueError, TypeError):
            duration = "unknown"

    lines = [
        f"# Postmortem: {inc['id']}",
        "",
        "## Summary",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| **Incident ID** | {inc['id']} |",
        f"| **Title** | {inc.get('title', '')} |",
        f"| **Severity** | {inc.get('severity', '?')} |",
        f"| **Trigger** | {inc.get('trigger', '?')} |",
        f"| **Duration** | {duration or 'ongoing'} |",
        f"| **Opened** | {inc.get('opened_at', '?')} |",
        f"| **Resolved** | {inc.get('resolved_at', 'N/A')} |",
        f"| **SLO** | {inc.get('slo_id', 'N/A')} |",
        "",
        "## Impact",
        "",
        f"{inc.get('description', 'No description provided.')}",
        "",
    ]

    if inc.get("blast_radius"):
        lines.append(f"**Blast Radius:** {', '.join(inc['blast_radius'])}")
    if inc.get("spof_tags"):
        lines.append(f"**Single Points of Failure:** {', '.join(inc['spof_tags'])}")

    lines.extend([
        "",
        "## Timeline",
        "",
        "| Time | Event | Detail | Actor |",
        "|------|-------|--------|-------|",
    ])

    for event in inc.get("timeline", []):
        ts = event.get("timestamp", "?")[:19]
        ev = event.get("event", "?")
        detail = event.get("detail", "").replace("|", "\\|")
        actor = event.get("actor", "")
        lines.append(f"| {ts} | {ev} | {detail} | {actor} |")

    lines.extend([
        "",
        "## Root Cause",
        "",
        f"Trigger: `{inc.get('trigger', '?')}`",
        "",
        "<!-- TODO: Fill in root cause analysis -->",
        "",
        "## Resolution",
        "",
        f"{inc.get('resolution_summary', 'Not yet resolved.')}",
        "",
        "## Actions Taken",
        "",
    ])

    if inc.get("actions_taken"):
        for a in inc["actions_taken"]:
            lines.append(f"- {a}")
    else:
        lines.append("- None recorded")

    lines.extend([
        "",
        "## Evidence",
        "",
    ])
    if inc.get("evidence_paths"):
        for p in inc["evidence_paths"]:
            lines.append(f"- `{p}`")
    else:
        lines.append("- No evidence attached")

    lines.extend([
        "",
        "## Lessons Learned",
        "",
        "<!-- TODO: What went well? What didn't? What to improve? -->",
        "",
        "## Action Items",
        "",
        "<!-- TODO: Follow-up tasks with owners and due dates -->",
        "",
        "| # | Action | Owner | Due | Status |",
        "|---|--------|-------|-----|--------|",
        "| 1 | | | | |",
        "",
        "---",
        f"*Generated: {datetime.now().isoformat()[:19]}*",
    ])

    return "\n".join(lines)


def save_incident_artifacts(incident_id: str):
    """Generate and save all markdown artifacts for an incident."""
    inc = load_incident(incident_id)
    if not inc:
        print(f"Incident {incident_id} not found.")
        return

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    # Incident page
    md = render_incident_md(inc)
    (ARTIFACTS_DIR / f"{incident_id}.md").write_text(md)

    # Timeline
    tl = render_timeline_md(inc)
    (ARTIFACTS_DIR / f"timeline_{incident_id}.md").write_text(tl)

    # Postmortem (only for resolved incidents)
    if inc.get("status") == "resolved":
        pm = render_postmortem_md(inc)
        (ARTIFACTS_DIR / f"postmortem_{incident_id}.md").write_text(pm)

        # Also save to services/openclaw/incidents/
        latest_pm_dir = ROOT_DIR.parent.parent.parent / "services" / "openclaw" / "incidents"
        latest_pm_dir.mkdir(parents=True, exist_ok=True)
        (latest_pm_dir / "latest_postmortem.md").write_text(pm)

        print(f"Postmortem generated: postmortem_{incident_id}.md")

    print(f"Artifacts saved for {incident_id}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        save_incident_artifacts(sys.argv[1])
    else:
        # Render latest active or most recent
        incidents = list_incidents()
        if incidents:
            save_incident_artifacts(incidents[0]["id"])
        else:
            print("No incidents to render.")
