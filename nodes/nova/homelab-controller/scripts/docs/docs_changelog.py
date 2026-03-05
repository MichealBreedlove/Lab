#!/usr/bin/env python3
"""P33 — Changelog Generator: auto-generate CHANGELOG.md from git history."""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT / "docs" / "generated"


def get_git_log(limit=100):
    """Get recent git commits."""
    try:
        r = subprocess.run(
            ["git", "-C", str(ROOT), "log", f"--max-count={limit}",
             "--format=%H|%ai|%s"],
            capture_output=True, text=True, timeout=15
        )
        if r.returncode != 0:
            return []
        return [line.split("|", 2) for line in r.stdout.strip().splitlines() if "|" in line]
    except Exception:
        return []


def parse_conventional_commit(subject):
    """Parse 'type(scope): description' format."""
    match = re.match(r'^(\w+)(?:\(([^)]+)\))?\s*:\s*(.+)$', subject)
    if match:
        return {
            "type": match.group(1),
            "scope": match.group(2),
            "description": match.group(3),
        }
    return {"type": "other", "scope": None, "description": subject}


def generate_changelog():
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    commits = get_git_log()

    # Group by type
    groups = {}
    for hash_val, date, subject in commits:
        parsed = parse_conventional_commit(subject)
        ctype = parsed["type"]
        if ctype not in groups:
            groups[ctype] = []
        groups[ctype].append({
            "hash": hash_val[:8],
            "date": date[:10],
            "scope": parsed["scope"],
            "description": parsed["description"],
        })

    # Type labels (Keep a Changelog style)
    type_labels = {
        "feat": "### Added",
        "fix": "### Fixed",
        "refactor": "### Changed",
        "docs": "### Documentation",
        "test": "### Testing",
        "chore": "### Maintenance",
        "other": "### Other",
    }

    lines = [
        "# Changelog",
        "",
        f"*Auto-generated from git history: {timestamp}*",
        "",
        "All notable changes to the homelab-controller are documented here.",
        "Format follows [Keep a Changelog](https://keepachangelog.com/).",
        "",
    ]

    for ctype in ["feat", "fix", "refactor", "docs", "test", "chore", "other"]:
        entries = groups.get(ctype, [])
        if not entries:
            continue
        lines.append(type_labels.get(ctype, f"### {ctype}"))
        lines.append("")
        for e in entries:
            scope = f"**{e['scope']}:** " if e["scope"] else ""
            lines.append(f"- {scope}{e['description']} (`{e['hash']}`, {e['date']})")
        lines.append("")

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "CHANGELOG.md").write_text("\n".join(lines))

    return {
        "file": "docs/generated/CHANGELOG.md",
        "commits_processed": len(commits),
        "types": {k: len(v) for k, v in groups.items()},
    }


def main():
    parser = argparse.ArgumentParser(description="Generate Changelog")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = generate_changelog()

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"📄 Generated: {result['file']} ({result['commits_processed']} commits)")
        for t, c in result["types"].items():
            print(f"  {t}: {c}")

    sys.exit(0)


if __name__ == "__main__":
    main()
