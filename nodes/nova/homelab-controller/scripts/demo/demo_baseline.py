#!/usr/bin/env python3
"""Phase 1: Collect baseline state before chaos injection."""
import json
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def check_port(host, port, timeout=3):
    try:
        s = socket.socket()
        s.settimeout(timeout)
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False


def main():
    demo_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")

    baseline = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "gateway": {
                "port_18789": check_port("10.1.1.150", 18789),
                "port_18080": check_port("10.1.1.150", 18080),
            },
            "ollama": {
                "port_11434": check_port("127.0.0.1", 11434) or check_port("10.1.1.150", 11434),
            },
            "nodes": {
                "nova_ssh": check_port("10.1.1.21", 22),
                "mira_ssh": check_port("10.1.1.22", 22),
                "orin_ssh": check_port("10.1.1.23", 22),
            }
        }
    }

    with open(demo_dir / "baseline.json", "w") as f:
        json.dump(baseline, f, indent=2)

    all_ok = all([
        baseline["services"]["gateway"]["port_18789"],
        baseline["services"]["ollama"]["port_11434"],
        baseline["services"]["nodes"]["nova_ssh"],
    ])

    status = "HEALTHY" if all_ok else "DEGRADED"
    print(f"  Baseline: {status}")
    for category, checks in baseline["services"].items():
        for name, ok in checks.items():
            icon = "[OK]" if ok else "[FAIL]"
            print(f"    {icon} {name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
