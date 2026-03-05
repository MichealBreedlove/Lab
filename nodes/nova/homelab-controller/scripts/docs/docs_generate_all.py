#!/usr/bin/env python3
"""P33 — Generate All Docs: run all documentation generators."""

import json
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent


def run_generator(name, script):
    try:
        r = subprocess.run(
            ["python3", str(SCRIPT_DIR / script), "--json"],
            capture_output=True, text=True, timeout=60
        )
        if r.returncode == 0:
            return {"name": name, "status": "ok", "result": json.loads(r.stdout)}
        return {"name": name, "status": "failed", "stderr": r.stderr[:200]}
    except Exception as e:
        return {"name": name, "status": "error", "error": str(e)}


def main():
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    generators = [
        ("topology", "docs_topology.py"),
        ("services", "docs_services.py"),
        ("dependencies", "docs_dependencies.py"),
        ("changelog", "docs_changelog.py"),
    ]

    results = []
    for name, script in generators:
        r = run_generator(name, script)
        results.append(r)
        icon = "✅" if r["status"] == "ok" else "❌"
        print(f"  {icon} {name}: {r['status']}")

    passing = sum(1 for r in results if r["status"] == "ok")
    total = len(results)

    print(f"\n📚 Documentation: {passing}/{total} generators succeeded ({timestamp})")
    sys.exit(0 if passing == total else 1)


if __name__ == "__main__":
    main()
