#!/usr/bin/env python3
"""Phase 5: Validate recovery - verify services are back."""
import json
import socket
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
    scenario = sys.argv[1] if len(sys.argv) > 1 else "gateway_restart_outage"
    demo_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".")

    validation = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scenario": scenario,
        "checks": [],
        "all_passed": False,
    }

    if scenario == "gateway_restart_outage":
        checks = [
            ("gateway_port_18789", check_port("10.1.1.150", 18789)),
            ("dashboard_port_18080", check_port("10.1.1.150", 18080)),
            ("nova_ssh", check_port("10.1.1.21", 22)),
        ]
    elif scenario == "ollama_unreachable":
        checks = [
            ("ollama_port_11434", check_port("127.0.0.1", 11434) or check_port("10.1.1.150", 11434)),
            ("nova_ssh", check_port("10.1.1.21", 22)),
            ("gateway_port_18789", check_port("10.1.1.150", 18789)),
        ]
    else:
        checks = []

    for name, passed in checks:
        validation["checks"].append({"check": name, "passed": passed})
        icon = "[OK]" if passed else "[FAIL]"
        print(f"    {icon} {name}")

    validation["all_passed"] = all(c["passed"] for c in validation["checks"])

    with open(demo_dir / "validation.json", "w") as f:
        json.dump(validation, f, indent=2)

    status = "ALL PASSED" if validation["all_passed"] else "SOME FAILED"
    print(f"  Recovery validation: {status}")
    return 0 if validation["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
