#!/usr/bin/env python3
"""Platform API — internal control interface for the homelab.
Listens on 0.0.0.0:8081, restricts to 10.1.1.0/24.
"""
import http.server
import ipaddress
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parent.parent.parent
BIND = os.environ.get("PLATFORM_BIND", "0.0.0.0")
PORT = int(os.environ.get("PLATFORM_PORT", "8081"))
ALLOWED_NETWORK = ipaddress.ip_network("10.1.1.0/24")
DASHBOARD_DATA = ROOT / "dashboard" / "static" / "data"

# Track last request for dashboard
_state = {
    "started_at": None,
    "last_request": None,
    "last_change": None,
    "request_count": 0,
}


def is_allowed(ip_str):
    """Check if IP is in the allowed LAN subnet or localhost."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip in ALLOWED_NETWORK or ip.is_loopback
    except ValueError:
        return False


def run_cmd(cmd, timeout=120):
    """Run a shell command, return (exit_code, stdout, stderr)."""
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=str(ROOT)
        )
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except Exception as e:
        return -1, "", str(e)


def create_change(trigger, summary):
    """Create a change log entry and return change_id."""
    rc, out, _ = run_cmd(
        f"python3 scripts/change/change_create.py {trigger} '{summary}'"
    )
    # Extract CHG-xxx from output
    for line in out.split("\n"):
        line = line.strip()
        if line.startswith("CHG-"):
            return line
    return None


def update_dashboard():
    """Write platform status to dashboard data."""
    DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)
    with open(DASHBOARD_DATA / "platform_status.json", "w") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "running",
            "port": PORT,
            "started_at": _state["started_at"],
            "last_request": _state["last_request"],
            "last_change": _state["last_change"],
            "request_count": _state["request_count"],
        }, f, indent=2)


class PlatformHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress default logging

    def _send_json(self, data, status=200):
        body = json.dumps(data, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _check_access(self):
        client_ip = self.client_address[0]
        if not is_allowed(client_ip):
            self._send_json({"error": "forbidden", "ip": client_ip}, 403)
            return False
        return True

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length > 0:
            try:
                return json.loads(self.rfile.read(length))
            except Exception:
                return {}
        return {}

    def _track(self, endpoint):
        _state["last_request"] = {
            "endpoint": endpoint,
            "time": datetime.now(timezone.utc).isoformat(),
            "ip": self.client_address[0],
        }
        _state["request_count"] += 1

    def do_GET(self):
        if not self._check_access():
            return

        path = urlparse(self.path).path.rstrip("/")

        if path == "" or path == "/":
            self._track("/")
            self._send_json({
                "service": "homelab-platform-api",
                "version": "1.0",
                "status": "running",
                "endpoints": ["/", "/topology", "/change", "/chaos", "/incident", "/snapshot"],
                "request_count": _state["request_count"],
            })

        elif path == "/topology":
            self._track("/topology")
            rc, out, _ = run_cmd("python3 scripts/controlplane/device_connectivity.py --json")
            try:
                data = json.loads(out)
            except Exception:
                data = {"raw": out}
            self._send_json({"topology": data})

        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        if not self._check_access():
            return

        path = urlparse(self.path).path.rstrip("/")
        body = self._read_body()

        if path == "/change":
            self._track("/change")
            trigger = body.get("trigger", "manual")
            summary = body.get("summary", "API-triggered change")

            change_id = create_change(trigger, summary)
            if change_id:
                run_cmd(f"python3 scripts/change/change_diff.py {change_id}")
                run_cmd(f"python3 scripts/change/change_validate.py {change_id}")
                run_cmd(f"python3 scripts/change/change_render.py {change_id}")
                _state["last_change"] = change_id
                update_dashboard()
                self._send_json({"change_id": change_id, "status": "completed"})
            else:
                self._send_json({"error": "failed to create change"}, 500)

        elif path == "/chaos":
            self._track("/chaos")
            scenario = body.get("scenario", "gateway_restart_outage")
            change_id = create_change("chaos_experiment", f"Chaos: {scenario}")

            rc, out, _ = run_cmd(f"bash scripts/demo/demo_runner.sh {scenario}")
            _state["last_change"] = change_id
            update_dashboard()
            self._send_json({
                "change_id": change_id,
                "scenario": scenario,
                "exit_code": rc,
                "output_lines": out.split("\n")[-10:],
            })

        elif path == "/incident":
            self._track("/incident")
            title = body.get("title", "Manual incident")
            severity = body.get("severity", "warning")
            change_id = create_change("remediation", f"Incident: {title}")

            _state["last_change"] = change_id
            update_dashboard()
            self._send_json({
                "change_id": change_id,
                "incident": {"title": title, "severity": severity},
                "status": "logged",
            })

        elif path == "/snapshot":
            self._track("/snapshot")
            change_id = create_change("controlplane_tick", "API-triggered snapshot")

            # Run drift + collect
            run_cmd("python3 scripts/drift/state_render_desired.py")
            run_cmd("python3 scripts/drift/state_collect_observed.py")
            rc_drift, out_drift, _ = run_cmd("python3 scripts/drift/state_drift.py")

            # Run change pipeline
            run_cmd(f"python3 scripts/change/change_diff.py {change_id}")
            run_cmd(f"python3 scripts/change/change_validate.py {change_id}")
            run_cmd(f"python3 scripts/change/change_render.py {change_id}")

            _state["last_change"] = change_id
            update_dashboard()

            # Read drift status
            drift_file = ROOT / "state" / "drift" / "drift_report.json"
            drift_status = "unknown"
            if drift_file.exists():
                with open(drift_file) as f:
                    drift_status = json.load(f).get("status", "unknown")

            self._send_json({
                "change_id": change_id,
                "drift_status": drift_status,
                "status": "completed",
            })

        else:
            self._send_json({"error": "not found"}, 404)


def main():
    _state["started_at"] = datetime.now(timezone.utc).isoformat()
    update_dashboard()

    server = http.server.HTTPServer((BIND, PORT), PlatformHandler)
    print(f"Platform API listening on {BIND}:{PORT}")
    print(f"Allowed network: {ALLOWED_NETWORK}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()


if __name__ == "__main__":
    main()
