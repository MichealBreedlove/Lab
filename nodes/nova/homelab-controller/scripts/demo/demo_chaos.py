#!/usr/bin/env python3
"""Phase 2: Inject chaos based on scenario."""
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

SCENARIOS = {
    "gateway_restart_outage": {
        "description": "Simulate gateway restart by stopping/starting the OpenClaw dashboard",
        "target": "dashboard_server",
        "action": "restart",
    },
    "ollama_unreachable": {
        "description": "Simulate Ollama becoming unreachable by blocking port temporarily",
        "target": "ollama",
        "action": "block_port",
    }
}


def main():
    scenario = sys.argv[1] if len(sys.argv) > 1 else "gateway_restart_outage"
    demo_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".")

    if scenario not in SCENARIOS:
        print(f"  [ERROR] Unknown scenario: {scenario}")
        print(f"  Available: {', '.join(SCENARIOS.keys())}")
        return 1

    spec = SCENARIOS[scenario]
    chaos = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scenario": scenario,
        "description": spec["description"],
        "target": spec["target"],
        "action": spec["action"],
        "injected": False,
        "simulated": True,
    }

    print(f"  Scenario: {spec['description']}")

    if scenario == "gateway_restart_outage":
        # Simulate: record that we would stop the dashboard, wait, restart
        chaos["steps"] = [
            {"action": "stop_service", "target": "dashboard_server", "simulated": True},
            {"action": "wait", "seconds": 5, "reason": "Simulate outage window"},
            {"action": "record_failure_window", "duration_sec": 5},
        ]
        print("  [SIM] Would stop dashboard server (port 18080)")
        print("  [SIM] Waiting 5s to simulate outage window...")
        time.sleep(2)  # Shortened for demo
        chaos["injected"] = True

    elif scenario == "ollama_unreachable":
        # Simulate: record that Ollama would be unreachable
        chaos["steps"] = [
            {"action": "block_port", "port": 11434, "simulated": True},
            {"action": "wait", "seconds": 5, "reason": "Simulate unreachable window"},
            {"action": "record_failure_window", "duration_sec": 5},
        ]
        print("  [SIM] Would block port 11434 (Ollama)")
        print("  [SIM] Waiting 5s to simulate outage window...")
        time.sleep(2)  # Shortened for demo
        chaos["injected"] = True

    with open(demo_dir / "chaos.json", "w") as f:
        json.dump(chaos, f, indent=2)

    print(f"  Chaos injected: {chaos['injected']} (simulated: {chaos['simulated']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
