#!/usr/bin/env python3
"""Render a change into a final markdown report and JSON summary."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CHANGES_DIR = ROOT / "changes"
DASHBOARD_DATA = ROOT / "dashboard" / "static" / "data"


def render_change(change_id):
    change_dir = CHANGES_DIR / change_id
    if not change_dir.exists():
        print(f"[ERROR] Change not found: {change_id}")
        return 1

    # Load all phase data
    change = {}
    for f in ["change.json", "diff.json", "validation.json"]:
        path = change_dir / f
        if path.exists():
            with open(path) as fh:
                change[f.replace(".json", "")] = json.load(fh)

    record = change.get("change", {})
    diff = change.get("diff", {})
    validation = change.get("validation", {})

    # Render markdown report
    lines = [
        f"# Change Report: {change_id}",
        f"",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Change ID | `{change_id}` |",
        f"| Trigger | {record.get('trigger', 'unknown')} |",
        f"| Summary | {record.get('summary', '')} |",
        f"| Author | {record.get('author', 'unknown')} |",
        f"| Created | {record.get('created_at', '')} |",
        f"| Status | {record.get('status', 'unknown')} |",
        f"",
    ]

    # Diff section
    lines.append("## Configuration Diff")
    diff_count = diff.get("diff_count", 0)
    if diff_count == 0:
        lines.append("No configuration changes detected.\n")
    else:
        lines.append(f"{diff_count} difference(s) found. See `diff.md` for details.\n")

    # Validation section
    lines.append("## Validation Results")
    passed = validation.get("passed", 0)
    failed = validation.get("failed", 0)
    lines.append(f"Passed: {passed} | Failed: {failed}\n")
    for c in validation.get("checks", []):
        icon = "[OK]" if c["passed"] else "[FAIL]"
        lines.append(f"- {icon} {c['name']}")
    lines.append("")

    # Evidence section
    evidence_dir = change_dir / "evidence"
    evidence_files = list(evidence_dir.glob("*")) if evidence_dir.exists() else []
    lines.append("## Evidence Pack")
    if evidence_files:
        for ef in evidence_files:
            lines.append(f"- `{ef.name}`")
    else:
        lines.append("No evidence files collected.")
    lines.append("")

    # Timeline
    lines.append("## Timeline")
    phases = record.get("phases", {})
    for phase, ts in phases.items():
        status = ts if ts else "(pending)"
        lines.append(f"- **{phase}**: {status}")

    with open(change_dir / "change.md", "w") as f:
        f.write("\n".join(lines) + "\n")

    # Update record
    record["phases"]["rendered"] = datetime.now(timezone.utc).isoformat()
    record["status"] = "rendered"
    with open(change_dir / "change.json", "w") as f:
        json.dump(record, f, indent=2)

    # Update dashboard data
    DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)

    # Recent changes list
    changes_index = []
    if CHANGES_DIR.exists():
        for d in sorted(CHANGES_DIR.iterdir(), reverse=True):
            if d.is_dir() and d.name.startswith("CHG-"):
                cf = d / "change.json"
                if cf.exists():
                    with open(cf) as fh:
                        c = json.load(fh)
                    changes_index.append({
                        "change_id": c.get("change_id"),
                        "trigger": c.get("trigger"),
                        "summary": c.get("summary", "")[:80],
                        "status": c.get("status"),
                        "created_at": c.get("created_at"),
                    })
                if len(changes_index) >= 20:
                    break

    with open(DASHBOARD_DATA / "changes_status.json", "w") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_changes": len(changes_index),
            "recent": changes_index[:10],
        }, f, indent=2)

    print(f"[OK] Change rendered: {change_dir}/change.md")
    return 0


def main():
    change_id = sys.argv[1] if len(sys.argv) > 1 else None
    if not change_id:
        if CHANGES_DIR.exists():
            dirs = sorted([d for d in CHANGES_DIR.iterdir() if d.is_dir() and d.name.startswith("CHG-")])
            if dirs:
                change_id = dirs[-1].name
    if not change_id:
        print("[ERROR] No change ID")
        return 1
    return render_change(change_id)


if __name__ == "__main__":
    sys.exit(main())
