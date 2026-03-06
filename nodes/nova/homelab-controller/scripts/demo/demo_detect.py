#!/usr/bin/env python3
"""Phase 3: Detect failure via monitoring signals."""
import json
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def check_port(host, port, timeout=2):
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

    detection = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scenario": scenario,
        "checks": [],
        "detected": False,
        "detection_method": "port_probe",
        "time_to_detect_sec": 0,
    }

    start = time.time()

    if scenario == "gateway_restart_outage":
        # In simulation mode, we detect based on SLO signal
        detection["checks"].append({
            "check": "dashboard_port_18080",
            "result": "simulated_failure",
            "signal": "SLO_VIOLATION: dashboard_availability < 99.9%",
        })
        detection["checks"].append({
            "check": "gateway_health_endpoint",
            "result": "simulated_timeout",
            "signal": "ALERT: GatewayUnreachable fired",
        })
        detection["detected"] = True

    elif scenario == "ollama_unreachable":
        detection["checks"].append({
            "check": "ollama_port_11434",
            "result": "simulated_failure",
            "signal": "SLO_VIOLATION: ollama_availability < 99.9%",
        })
        detection["checks"].append({
            "check": "model_inference_test",
            "result": "simulated_timeout",
            "signal": "ALERT: OllamaUnreachable fired",
        })
        detection["detected"] = True

    detection["time_to_detect_sec"] = round(time.time() - start, 2)

    with open(demo_dir / "detection.json", "w") as f:
        json.dump(detection, f, indent=2)

    status = "DETECTED" if detection["detected"] else "NOT DETECTED"
    print(f"  Failure: {status}")
    for check in detection["checks"]:
        print(f"    [{check['result']}] {check['check']}: {check['signal']}")
    print(f"  Detection time: {detection['time_to_detect_sec']}s")

    return 0


if __name__ == "__main__":
    sys.exit(main())
