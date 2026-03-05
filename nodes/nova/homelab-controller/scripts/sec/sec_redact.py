#!/usr/bin/env python3
"""P38 — Shared Redaction Library: used by all emitters for consistent secret removal."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"

# Default patterns (loaded from policy if available)
DEFAULT_PATTERNS = [
    (r'AKIA[0-9A-Z]{16}', 'REDACTED_AWS_KEY'),
    (r'ghp_[a-zA-Z0-9]{36}', 'REDACTED_GH_TOKEN'),
    (r'sk-[a-zA-Z0-9]{48}', 'REDACTED_API_KEY'),
    (r'-----BEGIN.*PRIVATE KEY-----.*?-----END.*PRIVATE KEY-----', 'REDACTED_PRIVATE_KEY'),
    (r'(password|passwd|secret|token)[\s=:]+\S+', r'\1=REDACTED'),
    (r'Bearer\s+[a-zA-Z0-9._-]{20,}', 'Bearer REDACTED'),
]


def load_patterns():
    """Load redaction patterns from security policy."""
    try:
        with open(CONFIG_DIR / "security_policy.json") as f:
            policy = json.load(f)
        patterns = []
        for p in policy.get("redaction_patterns", []):
            regex = p.get("regex")
            if regex:
                patterns.append((regex, f'REDACTED_{p.get("name", "").upper()}'))
        return patterns if patterns else DEFAULT_PATTERNS
    except Exception:
        return DEFAULT_PATTERNS


def redact(text, patterns=None):
    """Redact secrets from text using configured patterns."""
    if patterns is None:
        patterns = load_patterns()

    for regex, replacement in patterns:
        try:
            text = re.sub(regex, replacement, text, flags=re.IGNORECASE | re.DOTALL)
        except re.error:
            continue
    return text


def redact_json(data, patterns=None):
    """Redact secrets from a JSON-serializable object."""
    text = json.dumps(data, indent=2)
    return json.loads(redact(text, patterns))


def redact_file(path, output_path=None, patterns=None):
    """Redact secrets from a file."""
    content = Path(path).read_text()
    redacted = redact(content, patterns)
    if output_path:
        Path(output_path).write_text(redacted)
    return redacted


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(redact_file(sys.argv[1]))
    else:
        print("Usage: sec_redact.py <file>")
        print(f"Loaded {len(load_patterns())} redaction patterns")
