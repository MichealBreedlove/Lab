#!/usr/bin/env python3
"""Phase 4: Execute remediation via approval engine."""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def main():
    scenario = sys.argv[1] if len(sys.argv) > 1 else "gateway_restart_outage"
    demo_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".")

    remediation = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scenario": scenario,
        "approval": {"required": True, "granted": True, "method": "break_glass_simulated"},
        "actions": [],
        "success": False,
    }

    start = time.time()

    if scenario == "gateway_restart_outage":
        remediation["actions"] = [
            {"step": 1, "action": "check_process_status", "result": "dashboard_server not running"},
            {"step": 2, "action": "restart_dashboard_server", "command": "python3 server.py &", "result": "started"},
            {"step": 3, "action": "wait_for_port", "port": 18080, "timeout_sec": 30, "result": "port_open"},
            {"step": 4, "action": "verify_health_endpoint", "result": "200 OK"},
        ]
        print("  Remediation plan: restart dashboard server")
        for a in remediation["actions"]:
            print(f"    Step {a['step']}: {a['action']} -> {a['result']}")
            time.sleep(0.5)
        remediation["success"] = True

    elif scenario == "ollama_unreachable":
        remediation["actions"] = [
            {"step": 1, "action": "check_ollama_process", "result": "process running but port blocked"},
            {"step": 2, "action": "remove_port_block", "port": 11434, "result": "block removed"},
            {"step": 3, "action": "wait_for_port", "port": 11434, "timeout_sec": 30, "result": "port_open"},
            {"step": 4, "action": "verify_ollama_api", "endpoint": "/api/tags", "result": "200 OK"},
        ]
        print("  Remediation plan: unblock Ollama port")
        for a in remediation["actions"]:
            print(f"    Step {a['step']}: {a['action']} -> {a['result']}")
            time.sleep(0.5)
        remediation["success"] = True

    remediation["duration_sec"] = round(time.time() - start, 2)

    with open(demo_dir / "remediation.json", "w") as f:
        json.dump(remediation, f, indent=2)

    status = "SUCCESS" if remediation["success"] else "FAILED"
    print(f"  Remediation: {status} ({remediation['duration_sec']}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
