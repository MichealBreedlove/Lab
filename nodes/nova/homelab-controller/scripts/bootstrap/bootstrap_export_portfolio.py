#!/usr/bin/env python3
"""P31 — Bootstrap Export: sanitize and export bootstrap artifacts to Lab/ for portfolio."""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "artifacts" / "bootstrap"
CONFIG_DIR = ROOT / "config"

# Patterns to redact
SECRET_PATTERNS = [
    (re.compile(r'(token["\s:=]+)["\']?[a-f0-9]{32,}["\']?', re.I), r'\1"REDACTED"'),
    (re.compile(r'(password["\s:=]+)["\']?[^\s"\']+["\']?', re.I), r'\1"REDACTED"'),
    (re.compile(r'(AKIA[0-9A-Z]{16})'), 'REDACTED_AWS_KEY'),
    (re.compile(r'(ghp_[a-zA-Z0-9]{36})'), 'REDACTED_GH_TOKEN'),
    (re.compile(r'(sk-[a-zA-Z0-9]{48})'), 'REDACTED_API_KEY'),
    (re.compile(r'-----BEGIN.*PRIVATE KEY-----.*?-----END.*PRIVATE KEY-----', re.S), 'REDACTED_PRIVATE_KEY'),
    (re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'), lambda m: m.group() if m.group().startswith('10.1.1.') else 'X.X.X.X'),
]


def sanitize(text):
    """Remove secrets from text content."""
    for pattern, replacement in SECRET_PATTERNS:
        if callable(replacement):
            text = pattern.sub(replacement, text)
        else:
            text = pattern.sub(replacement, text)
    return text


def load_json(path):
    with open(path) as f:
        return json.load(f)


def export(lab_repo_path):
    lab = Path(lab_repo_path)
    export_dir = lab / "exports" / "bootstrap"
    export_dir.mkdir(parents=True, exist_ok=True)

    exported = []

    # Export bootstrap policy (sanitized)
    policy_src = CONFIG_DIR / "bootstrap_policy.json"
    if policy_src.exists():
        data = sanitize(policy_src.read_text())
        dst = export_dir / "bootstrap_policy_sanitized.json"
        dst.write_text(data)
        exported.append(str(dst.relative_to(lab)))

    # Export node profiles (sanitized)
    profiles_src = CONFIG_DIR / "node_profiles.json"
    if profiles_src.exists():
        data = sanitize(profiles_src.read_text())
        dst = export_dir / "node_profiles_sanitized.json"
        dst.write_text(data)
        exported.append(str(dst.relative_to(lab)))

    # Export per-node artifacts
    for art_file in ARTIFACTS_DIR.glob("*.json"):
        data = sanitize(art_file.read_text())
        dst = export_dir / f"{art_file.stem}_sanitized.json"
        dst.write_text(data)
        exported.append(str(dst.relative_to(lab)))

    # Create summary
    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": "homelab-controller/scripts/bootstrap/bootstrap_export_portfolio.py",
        "files_exported": exported,
        "sanitization": "Tokens, passwords, private keys, and non-local IPs redacted",
        "note": "These artifacts demonstrate bootstrap automation patterns. All sensitive values removed.",
    }
    summary_dst = export_dir / "export_summary.json"
    with open(summary_dst, "w") as f:
        json.dump(summary, f, indent=2)
    exported.append(str(summary_dst.relative_to(lab)))

    # Secret scan
    violations = 0
    for f_path in export_dir.glob("*.json"):
        content = f_path.read_text()
        for pattern, _ in SECRET_PATTERNS[:5]:  # Check the explicit secret patterns
            if pattern.search(content) and 'REDACTED' not in pattern.search(content).group():
                violations += 1

    return {
        "exported": exported,
        "violations": violations,
        "export_dir": str(export_dir),
    }


def main():
    parser = argparse.ArgumentParser(description="Bootstrap Portfolio Export")
    parser.add_argument("--lab-repo", required=True, help="Path to Lab repo root")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = export(args.lab_repo)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"📦 Exported {len(result['exported'])} files to {result['export_dir']}")
        for f in result["exported"]:
            print(f"  • {f}")
        if result["violations"] > 0:
            print(f"  ⚠️  {result['violations']} potential secret violations found!")
        else:
            print("  ✅ Secret scan clean")

    sys.exit(1 if result["violations"] > 0 else 0)


if __name__ == "__main__":
    main()
