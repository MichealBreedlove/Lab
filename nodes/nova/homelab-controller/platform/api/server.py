#!/usr/bin/env python3
"""Platform API — internal control interface for the homelab.
Listens on 0.0.0.0:8081, restricts to 10.1.1.0/24.
All endpoints require Bearer token auth with role-based enforcement (P48).
"""
import http.server
import ipaddress
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parent.parent.parent
BIND = os.environ.get("PLATFORM_BIND", "0.0.0.0")
PORT = int(os.environ.get("PLATFORM_PORT", "8081"))
ALLOWED_NETWORK = ipaddress.ip_network("10.1.1.0/24")
DASHBOARD_DATA = ROOT / "dashboard" / "static" / "data"
API_AUDIT_FILE = ROOT / "artifacts" / "identity" / "api_audit.jsonl"

# Add identity scripts to path
sys.path.insert(0, str(ROOT / "scripts" / "identity"))

_state = {
    "started_at": None,
    "last_request": None,
    "last_change": None,
    "request_count": 0,
    "failed_auth_count": 0,
}

# Endpoint -> minimum role mapping
# Roles ranked: viewer < operator < sre < admin
ROLE_RANK = {"viewer": 0, "operator": 1, "automation": 1, "sre": 2, "admin": 3}
ENDPOINT_ROLES = {
    "GET:/":           "viewer",
    "GET:/topology":   "viewer",
    "GET:/incidents":  "viewer",
    "GET:/events":     "viewer",
    "POST:/investigate": "sre",
    "POST:/remediation/artifact": "sre",
    "POST:/change":    "operator",
    "POST:/snapshot":  "operator",
    "POST:/incident":  "operator",
    "POST:/recover":   "sre",
    "POST:/failover":  "sre",
    "POST:/events/alertmanager": "automation",
    "POST:/chaos":     "sre",
}


def is_allowed(ip_str):
    try:
        ip = ipaddress.ip_address(ip_str)
        return ip in ALLOWED_NETWORK or ip.is_loopback
    except ValueError:
        return False


def run_cmd(cmd, timeout=120):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           timeout=timeout, cwd=str(ROOT))
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except Exception as e:
        return -1, "", str(e)


def create_change(trigger, summary):
    rc, out, _ = run_cmd(f"python3 scripts/change/change_create.py {trigger} '{summary}'")
    for line in out.split("\n"):
        line = line.strip()
        if line.startswith("CHG-"):
            return line
    return None


def audit_api(token_id, role, endpoint, method, status, source_ip, details=None):
    """Append an API audit entry."""
    API_AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "token_id": token_id or "none",
        "role": role or "none",
        "endpoint": endpoint,
        "action": method,
        "status": status,
        "source_ip": source_ip,
        "details": details or {},
    }
    with open(API_AUDIT_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def update_dashboard():
    DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)
    with open(DASHBOARD_DATA / "platform_status.json", "w") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "running",
            "port": PORT,
            "auth_required": True,
            "rate_limit_enabled": True,
            "tls_configured": Path(ROOT / "deploy" / "caddy" / "Caddyfile").exists(),
            "recovery_enabled": Path(ROOT / "config" / "recovery_policy.json").exists(),
            "started_at": _state["started_at"],
            "last_request": _state["last_request"],
            "last_change": _state["last_change"],
            "request_count": _state["request_count"],
            "failed_auth_count": _state["failed_auth_count"],
        }, f, indent=2)


class PlatformHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send_json(self, data, status=200):
        body = json.dumps(data, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _client_ip(self):
        return self.client_address[0]

    def _check_network(self):
        if not is_allowed(self._client_ip()):
            self._send_json({"error": "forbidden", "ip": self._client_ip()}, 403)
            return False
        return True

    def _authenticate(self, method, endpoint):
        """Validate Bearer token and check role. Returns (allowed, token_id, role)."""
        ip = self._client_ip()

        # Extract token from Authorization header
        auth_header = self.headers.get("Authorization", "")
        token_secret = None
        if auth_header.startswith("Bearer "):
            token_secret = auth_header[7:].strip()

        if not token_secret:
            _state["failed_auth_count"] += 1
            audit_api(None, None, endpoint, method, "401_no_token", ip)
            self._send_json({"error": "unauthorized", "message": "Bearer token required"}, 401)
            return False, None, None

        # Validate token
        try:
            from token_issuer import validate_token
            result = validate_token(token_secret)
        except Exception as e:
            _state["failed_auth_count"] += 1
            audit_api(None, None, endpoint, method, "401_error", ip, {"error": str(e)})
            self._send_json({"error": "unauthorized", "message": "Token validation failed"}, 401)
            return False, None, None

        if not result:
            _state["failed_auth_count"] += 1
            audit_api(None, None, endpoint, method, "401_invalid", ip)
            self._send_json({"error": "unauthorized", "message": "Invalid or expired token"}, 401)
            return False, None, None

        token_id = result["token_id"]
        role = result["role"]

        # Check service account enabled state
        try:
            from token_issuer import load_tokens
            tokens_data = load_tokens()
            for t in tokens_data.get("tokens", []):
                if t.get("token_id") == token_id and t.get("principal_type") == "service_account":
                    sa_name = t.get("service_account", "")
                    if sa_name:
                        sys.path.insert(0, str(ROOT / "scripts" / "identity"))
                        from service_accounts import is_sa_enabled
                        if not is_sa_enabled(sa_name):
                            _state["failed_auth_count"] += 1
                            audit_api(token_id, role, endpoint, method, "401_sa_disabled", ip)
                            self._send_json({"error": "unauthorized",
                                             "message": f"Service account '{sa_name}' is disabled"}, 401)
                            return False, token_id, role
                    break
        except Exception:
            pass

        # Check role permission
        endpoint_key = f"{method}:{endpoint}"
        required_role = ENDPOINT_ROLES.get(endpoint_key, "admin")
        required_rank = ROLE_RANK.get(required_role, 3)
        user_rank = ROLE_RANK.get(role, -1)

        if user_rank < required_rank:
            _state["failed_auth_count"] += 1
            audit_api(token_id, role, endpoint, method, "403_insufficient_role", ip,
                      {"required": required_role})
            self._send_json({
                "error": "forbidden",
                "message": f"Role '{role}' cannot access {endpoint} (requires '{required_role}')",
            }, 403)
            return False, token_id, role

        # Rate limit check
        try:
            from rate_limit import check_rate_limit
            allowed_rl, limit, remaining, reset_at = check_rate_limit(token_id, role)
            if not allowed_rl:
                _state["failed_auth_count"] += 1
                audit_api(token_id, role, endpoint, method, "429_rate_limited", ip,
                          {"limit": limit})
                self._send_json({
                    "error": "too many requests",
                    "message": f"Rate limit exceeded for role '{role}'",
                    "role": role,
                    "limit": limit,
                }, 429)
                return False, token_id, role
        except ImportError:
            pass  # rate_limit module not available, skip

        # Authorized
        audit_api(token_id, role, endpoint, method, "200_authorized", ip)
        return True, token_id, role

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length > 0:
            try:
                return json.loads(self.rfile.read(length))
            except Exception:
                return {}
        return {}

    def _track(self, endpoint, token_id=None, role=None):
        _state["last_request"] = {
            "endpoint": endpoint,
            "time": datetime.now(timezone.utc).isoformat(),
            "ip": self._client_ip(),
            "token_id": token_id,
            "role": role,
        }
        _state["request_count"] += 1

    def do_GET(self):
        if not self._check_network():
            return
        path = urlparse(self.path).path.rstrip("/") or "/"
        allowed, token_id, role = self._authenticate("GET", path)
        if not allowed:
            return

        if path == "/":
            self._track("/", token_id, role)
            self._send_json({
                "service": "homelab-platform-api",
                "version": "2.2",
                "status": "running",
                "auth": {"token_id": token_id, "role": role},
                "rate_limit_enabled": True,
                "tls_configured": Path(ROOT / "deploy" / "caddy" / "Caddyfile").exists(),
                "recovery_enabled": Path(ROOT / "config" / "recovery_policy.json").exists(),
                "event_bus_enabled": True,
                "remediation_artifacts_enabled": Path(ROOT / "config" / "aiops_policy.json").exists(),
                "endpoints": ["/", "/topology", "/events", "/events/alertmanager",
                              "/incidents", "/change", "/chaos", "/incident", "/snapshot",
                              "/recover", "/failover", "/investigate", "/remediation/artifact"],
                "request_count": _state["request_count"],
            })
        elif path == "/topology":
            self._track("/topology", token_id, role)
            rc, out, _ = run_cmd("python3 scripts/controlplane/device_connectivity.py --json")
            try:
                data = json.loads(out)
            except Exception:
                data = {"raw": out}
            self._send_json({"topology": data})
        elif path == "/events":
            self._track("/events", token_id, role)
            params = parse_qs(urlparse(self.path).query)
            etype = params.get("type", [None])[0]
            inc_id = params.get("incident_id", [None])[0]
            lim = int(params.get("limit", ["50"])[0])
            sys.path.insert(0, str(ROOT / "platform" / "events"))
            from bus import query as event_query
            events = event_query(event_type=etype, incident_id=inc_id, limit=lim)
            self._send_json({"events": events, "count": len(events)})
        elif path == "/incidents":
            self._track("/incidents", token_id, role)
            inc_file = ROOT / "artifacts" / "recovery" / "incidents.json"
            if inc_file.exists():
                with open(inc_file) as f:
                    data = json.load(f)
                self._send_json({"incidents": data.get("incidents", [])[-20:]})
            else:
                self._send_json({"incidents": []})
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        if not self._check_network():
            return
        path = urlparse(self.path).path.rstrip("/")
        allowed, token_id, role = self._authenticate("POST", path)
        if not allowed:
            return

        body = self._read_body()

        if path == "/events/alertmanager":
            self._track("/events/alertmanager", token_id, role)
            sys.path.insert(0, str(ROOT / "platform" / "events"))
            from alert_ingest import ingest_alertmanager_payload
            results = ingest_alertmanager_payload(body)
            self._send_json({
                "status": "accepted",
                "processed": len(results),
                "results": [{"action": r["action"],
                              "incident_id": r["incident"]["incident_id"]}
                             for r in results],
            })

        elif path == "/change":
            self._track("/change", token_id, role)
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
            self._track("/chaos", token_id, role)
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
            self._track("/incident", token_id, role)
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

        elif path == "/recover":
            self._track("/recover", token_id, role)
            service = body.get("service", "")
            dry_run = body.get("dry_run", True)
            if not service:
                self._send_json({"error": "service required"}, 400)
            else:
                rc, out, _ = run_cmd(
                    f"python3 platform/recovery/engine.py check {service}"
                    + (" --dry-run" if dry_run else ""))
                self._send_json({"service": service, "output": out.split("\n")[-5:], "dry_run": dry_run})

        elif path == "/failover":
            self._track("/failover", token_id, role)
            service = body.get("service", "")
            dry_run = body.get("dry_run", True)
            if not service:
                self._send_json({"error": "service required"}, 400)
            else:
                rc, out, _ = run_cmd(
                    f"python3 platform/recovery/engine.py check {service}"
                    + (" --dry-run" if dry_run else ""))
                self._send_json({"service": service, "output": out.split("\n")[-5:], "dry_run": dry_run})

        elif path == "/remediation/artifact":
            self._track("/remediation/artifact", token_id, role)
            inc_id = body.get("incident_id")
            inv_id = body.get("investigation_id")
            patch = body.get("include_patch_plan", True)
            rc, out, _ = run_cmd(
                f"python3 platform/aiops/remediator.py generate"
                + (f" {inc_id}" if inc_id else "")
                + (f" {inv_id}" if inv_id else "")
                + ("" if patch else " --no-patch"))
            # List generated files
            rem_dir = ROOT / "data" / "remediation" / "incidents"
            files = []
            if rem_dir.exists() and inc_id:
                files = [f.name for f in rem_dir.glob(f"{inc_id}-*")]
            self._send_json({"incident_id": inc_id, "artifacts": files, "output": out.split("\n")[-5:]})

        elif path == "/investigate":
            self._track("/investigate", token_id, role)
            inc_id = body.get("incident_id", "INC-API")
            service = body.get("service", "api")
            state = body.get("state", "confirmed")
            simulate = body.get("simulate", True)
            rc, out, _ = run_cmd(
                f"python3 platform/aiops/investigator.py run {inc_id} {service} {state}"
                + (" --simulate" if simulate else ""))
            # Read latest investigation
            inv_dir = ROOT / "data" / "incidents" / "investigations"
            inv_data = {}
            if inv_dir.exists():
                files = sorted(inv_dir.glob("INV-*.json"))
                if files:
                    with open(files[-1]) as f:
                        inv_data = json.load(f)
            self._send_json({"investigation": inv_data})

        elif path == "/snapshot":
            self._track("/snapshot", token_id, role)
            change_id = create_change("controlplane_tick", "API-triggered snapshot")
            run_cmd("python3 scripts/drift/state_render_desired.py")
            run_cmd("python3 scripts/drift/state_collect_observed.py")
            run_cmd("python3 scripts/drift/state_drift.py")
            run_cmd(f"python3 scripts/change/change_diff.py {change_id}")
            run_cmd(f"python3 scripts/change/change_validate.py {change_id}")
            run_cmd(f"python3 scripts/change/change_render.py {change_id}")
            _state["last_change"] = change_id
            update_dashboard()
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
    print(f"Platform API v2.2 listening on {BIND}:{PORT}")
    print(f"Auth: Bearer token required (RBAC enforced)")
    print(f"Network: {ALLOWED_NETWORK}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()


if __name__ == "__main__":
    main()
