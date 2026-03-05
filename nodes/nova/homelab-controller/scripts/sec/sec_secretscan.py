#!/usr/bin/env python3
"""P38 — Secret Scanner: scan repository for leaked secrets, block on violations."""

import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "artifacts" / "security"
CONFIG_DIR = ROOT / "config"

PATTERNS = [
    ("aws_key", re.compile(r'AKIA[0-9A-Z]{16}')),
    ("github_token", re.compile(r'ghp_[a-zA-Z0-9]{36}')),
    ("openai_key", re.compile(r'sk-[a-zA-Z0-9]{48}')),
    ("private_key", re.compile(r'-----BEGIN.*PRIVATE KEY-----')),
    ("generic_secret", re.compile(r'(?:password|secret|token|api_key)\s*[=:]\s*["\'][^"\']{8,}["\']', re.I)),
]

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "artifacts"}
SCAN_EXTENSIONS = {".json", ".py", ".sh", ".ps1", ".md", ".yaml", ".yml", ".toml", ".cfg", ".conf", ".env", ".txt"}

# Regex-aware false positive filter: if the match contains regex metacharacters
# like .* or [A-Z] or \S+, it's a pattern definition, not an actual secret
FALSE_POSITIVE_INDICATORS = re.compile(r'(\.\*|\[[\w-]+\]|\\[sSdDwW]|\{[\d,]+\}|^\^|\\b)')



def scan(root_path=None):
    if root_path is None:
        root_path = ROOT

    violations = []
    files_scanned = 0

    for f in Path(root_path).rglob("*"):
        if f.is_dir():
            continue
        if any(skip in f.parts for skip in SKIP_DIRS):
            continue
        if f.suffix not in SCAN_EXTENSIONS:
            continue

        files_scanned += 1
        try:
            content = f.read_text(errors="ignore")
        except Exception:
            continue

        for name, pattern in PATTERNS:
            matches = pattern.findall(content)
            if matches:
                # Filter out false positives: regex pattern definitions, not real secrets
                real_matches = [m for m in matches if not FALSE_POSITIVE_INDICATORS.search(m)]
                if real_matches:
                    violations.append({
                        "file": str(f.relative_to(root_path)),
                        "pattern": name,
                        "count": len(real_matches),
                        "sample": real_matches[0][:20] + "..." if len(real_matches[0]) > 20 else real_matches[0],
                    })

    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    result = {
        "timestamp": timestamp,
        "files_scanned": files_scanned,
        "violations": violations,
        "violation_count": len(violations),
        "pass": len(violations) == 0,
    }

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(ARTIFACTS_DIR / "secretscan_latest.json", "w") as f_out:
        json.dump(result, f_out, indent=2)

    return result


def main():
    parser = argparse.ArgumentParser(description="Secret Scanner")
    parser.add_argument("--path", default=None, help="Path to scan (default: homelab-controller)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = scan(args.path)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["pass"]:
            print(f"✅ Secret scan clean ({result['files_scanned']} files scanned)")
        else:
            print(f"🚨 {result['violation_count']} secret violations found!")
            for v in result["violations"]:
                print(f"  ❌ {v['file']}: {v['pattern']} ({v['count']}x)")

    sys.exit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
