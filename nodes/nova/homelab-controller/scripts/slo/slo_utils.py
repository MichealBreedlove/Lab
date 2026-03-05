#!/usr/bin/env python3
"""slo_utils.py — Shared utilities for SLO pipeline."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent.parent
CONFIG_DIR = ROOT_DIR / "config"
ARTIFACTS_DIR = ROOT_DIR / "artifacts" / "slo"


def load_json(path: Path) -> dict:
    """Load a JSON file."""
    with open(path) as f:
        return json.load(f)


def save_json(path: Path, data: dict, indent: int = 2):
    """Save data as JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=indent, default=str)


def load_policy() -> dict:
    """Load SLO policy config."""
    return load_json(CONFIG_DIR / "slo_policy.json")


def load_catalog() -> dict:
    """Load SLO catalog."""
    return load_json(CONFIG_DIR / "slo_catalog.json")


def load_state() -> dict:
    """Load pipeline state (last run, cursors, etc.)."""
    state_file = ARTIFACTS_DIR / "state.json"
    if state_file.exists():
        return load_json(state_file)
    return {
        "last_run": None,
        "last_daily_report": None,
        "last_weekly_report": None,
        "slo_states": {}
    }


def save_state(state: dict):
    """Persist pipeline state."""
    save_json(ARTIFACTS_DIR / "state.json", state)


def now_iso() -> str:
    """Current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def today_str() -> str:
    """Today's date as YYYY-MM-DD."""
    return datetime.now().strftime("%Y-%m-%d")


def week_str() -> str:
    """Current ISO week as YYYY-WW."""
    now = datetime.now()
    return f"{now.year}-W{now.isocalendar()[1]:02d}"


def append_jsonl(path: Path, record: dict):
    """Append a JSON record to a JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")


def read_jsonl(path: Path, max_lines: int = None) -> list:
    """Read records from a JSONL file."""
    if not path.exists():
        return []
    records = []
    with open(path) as f:
        for i, line in enumerate(f):
            if max_lines and i >= max_lines:
                break
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records
