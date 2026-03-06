#!/usr/bin/env python3
"""Compare previous config state vs new state for a change."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CHANGES_DIR = ROOT / "changes"
STATE_DIR = ROOT / "state"


def load_json(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def dict_diff(old, new, prefix=""):
    """Recursively diff two dicts. Returns list of changes."""
    diffs = []
    all_keys = set(list(old.keys()) + list(new.keys()))
    for key in sorted(all_keys):
        path = f"{prefix}.{key}" if prefix else key
        old_val = old.get(key)
        new_val = new.get(key)
        if old_val == new_val:
            continue
        if isinstance(old_val, dict) and isinstance(new_val, dict):
            diffs.extend(dict_diff(old_val, new_val, path))
        else:
            diffs.append({
                "path": path,
                "old": old_val,
                "new": new_val,
            })
    return diffs


def diff_change(change_id):
    """Generate diff for a change by comparing drift states."""
    change_dir = CHANGES_DIR / change_id
    if not change_dir.exists():
        print(f"[ERROR] Change not found: {change_id}")
        return 1

    # Compare current observed vs desired (drift-style)
    diffs = []
    for node_dir in sorted((STATE_DIR / "observed").iterdir()):
        if not node_dir.is_dir():
            continue
        observed = load_json(node_dir / "observed.json")
        desired_path = STATE_DIR / "desired" / node_dir.name / "desired.json"
        desired = load_json(desired_path)
        if observed and desired:
            node_diffs = dict_diff(desired, observed, node_dir.name)
            diffs.extend(node_diffs)

    # Save diff JSON
    diff_record = {
        "change_id": change_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "diff_count": len(diffs),
        "diffs": diffs,
    }

    with open(change_dir / "diff.json", "w") as f:
        json.dump(diff_record, f, indent=2)

    # Render diff markdown
    lines = [
        f"# Config Diff -- {change_id}",
        f"",
        f"Changes detected: **{len(diffs)}**",
        f"",
    ]
    if not diffs:
        lines.append("No configuration differences found.")
    else:
        lines.append("| Path | Previous | Current |")
        lines.append("|------|----------|---------|")
        for d in diffs[:50]:  # Cap at 50
            old = str(d["old"])[:40] if d["old"] is not None else "(none)"
            new = str(d["new"])[:40] if d["new"] is not None else "(none)"
            lines.append(f"| `{d['path']}` | {old} | {new} |")

    with open(change_dir / "diff.md", "w") as f:
        f.write("\n".join(lines) + "\n")

    # Update change record
    change_file = change_dir / "change.json"
    if change_file.exists():
        with open(change_file) as f:
            record = json.load(f)
        record["phases"]["diffed"] = datetime.now(timezone.utc).isoformat()
        with open(change_file, "w") as f:
            json.dump(record, f, indent=2)

    print(f"[OK] Diff generated: {len(diffs)} change(s)")
    return 0


def main():
    change_id = sys.argv[1] if len(sys.argv) > 1 else None
    if not change_id:
        # Find latest change
        if CHANGES_DIR.exists():
            dirs = sorted([d for d in CHANGES_DIR.iterdir() if d.is_dir() and d.name.startswith("CHG-")])
            if dirs:
                change_id = dirs[-1].name
    if not change_id:
        print("[ERROR] No change ID specified and no changes found")
        return 1
    return diff_change(change_id)


if __name__ == "__main__":
    sys.exit(main())
