#!/usr/bin/env python3
"""portfolio_redact.py — Sanitize content before publishing to GitHub Pages.

Scans markdown/json/yml/sh/ps1 for secrets + PII patterns and redacts them.
"""

import re
import json
from pathlib import Path
from typing import List, Tuple

SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent.parent
CONFIG_DIR = ROOT_DIR / "config"


def load_policy() -> dict:
    with open(CONFIG_DIR / "portfolio_policy.json") as f:
        return json.load(f)


# Compiled patterns (loaded once)
DEFAULT_PATTERNS = [
    (r'sk-[a-zA-Z0-9]{20,}', 'sk-REDACTED'),
    (r'ghp_[a-zA-Z0-9]{36}', 'ghp_REDACTED'),
    (r'gho_[a-zA-Z0-9]{36}', 'gho_REDACTED'),
    (r'glpat-[a-zA-Z0-9\-]{20,}', 'glpat-REDACTED'),
    (r'-----BEGIN[A-Z ]*PRIVATE KEY-----[\s\S]*?-----END[A-Z ]*PRIVATE KEY-----',
     '[PRIVATE KEY REDACTED]'),
    (r'Bearer [a-zA-Z0-9\.\-_]{20,}', 'Bearer REDACTED'),
    (r'"token"\s*:\s*"[^"]+"', '"token": "REDACTED"'),
    (r'"password"\s*:\s*"[^"]+"', '"password": "REDACTED"'),
    (r'"apiKey"\s*:\s*"[^"]+"', '"apiKey": "REDACTED"'),
    (r'"api_key"\s*:\s*"[^"]+"', '"api_key": "REDACTED"'),
]

EMAIL_PATTERN = (r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[EMAIL REDACTED]')
PHONE_PATTERN = (r'\+1[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}', '[PHONE REDACTED]')

SCANNABLE_EXTENSIONS = {'.md', '.json', '.yml', '.yaml', '.sh', '.ps1',
                        '.py', '.ini', '.cfg', '.conf', '.txt', '.j2', '.html'}


def redact_content(content: str, policy: dict = None) -> Tuple[str, int]:
    """Redact secrets and PII from content.

    Returns (redacted_content, count_of_redactions)
    """
    if policy is None:
        policy = load_policy()

    redaction_config = policy.get("redaction", {})
    count = 0

    # Always redact tokens and keys
    for pattern, replacement in DEFAULT_PATTERNS:
        matches = len(re.findall(pattern, content))
        if matches:
            content = re.sub(pattern, replacement, content)
            count += matches

    # Optional: emails
    if redaction_config.get("emails", True):
        p, r = EMAIL_PATTERN
        matches = len(re.findall(p, content))
        if matches:
            content = re.sub(p, r, content)
            count += matches

    # Optional: phone numbers
    if redaction_config.get("phone_numbers", True):
        p, r = PHONE_PATTERN
        matches = len(re.findall(p, content))
        if matches:
            content = re.sub(p, r, content)
            count += matches

    return content, count


def redact_file(filepath: Path, policy: dict = None) -> int:
    """Redact a single file in-place. Returns count of redactions."""
    if filepath.suffix not in SCANNABLE_EXTENSIONS:
        return 0

    try:
        content = filepath.read_text(encoding='utf-8', errors='replace')
    except Exception:
        return 0

    redacted, count = redact_content(content, policy)

    if count > 0:
        filepath.write_text(redacted, encoding='utf-8')

    return count


def redact_directory(dirpath: Path, policy: dict = None) -> int:
    """Redact all files in a directory tree. Returns total redactions."""
    if policy is None:
        policy = load_policy()

    total = 0
    for filepath in dirpath.rglob("*"):
        if filepath.is_file() and filepath.suffix in SCANNABLE_EXTENSIONS:
            count = redact_file(filepath, policy)
            if count > 0:
                print(f"  Redacted {count} items in {filepath}")
                total += count

    return total


if __name__ == "__main__":
    import sys
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT_DIR
    total = redact_directory(target)
    print(f"\nTotal redactions: {total}")
