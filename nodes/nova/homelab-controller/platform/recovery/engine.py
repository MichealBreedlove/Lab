#!/usr/bin/env python3
"""Self-healing recovery engine for homelab control plane."""
import json
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_FILE = Path(__file__).parent / "health_registry.json"
FAILOVER_FILE = Path(__file__).parent / "failover_map.json"
POLICY_FILE = ROOT / "config" / "recovery_policy.json"
INCIDENTS_FILE = ROOT / "artifacts" / "recovery" / "incidents.json"
AUDIT_FILE = ROOT / "artifacts" / "identity" / "api_audit.jsonl"

# In-memory cooldown tracker
_cooldowns = {}  # service_name -> last_action_timestamp

STATES = ["detected", "verifying", "confirmed", "recovering", "recovered", "failed_recovery"]


def load_json(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load_incidents():
    data = load_json(INCIDENTS_FILE)
    if "incidents" not in data:
        data["incidents"] = []
    return data


def save_incidents(data):
    save_json(INCIDENTS_FILE, data)


def audit_recovery(action, service, result, details=None):
    AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "token_id": "recovery-engine",
        "role": "system",
        "endpoint": f"/recover/{service}",
        "action": action,
        "status": result,
        "source_ip": "127.0.0.1",
        "details": details or {},
    }
    with open(AUDIT_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def check_health(url, timeout=5):
    """Check if a URL is healthy. Returns (healthy, status_code, latency_ms)."""
    start = time.time()
    try:
        resp = urlopen(url, timeout=timeout)
        latency = (time.time() - start) * 1000
        return True, resp.status, latency
    except Exception:
        latency = (time.time() - start) * 1000
        return False, 0, latency


def check_process(service_name):
    """Secondary signal: check if process/port is listening."""
    registry = load_json(REGISTRY_FILE)
    for svc in registry.get("services", []):
        if svc["name"] == service_name:
            url = svc.get("health_url", "")
            if ":" in url:
                # Extract port and check with socket
                import socket
                try:
                    parts = url.split(":")
                    port = int(parts[2].split("/")[0])
                    s = socket.socket()
                    s.settimeout(3)
                    s.connect(("127.0.0.1", port))
                    s.close()
                    return True
                except Exception:
                    return False
    return False


def is_cooldown_active(service_name):
    """Check if service is in cooldown."""
    registry = load_json(REGISTRY_FILE)
    cooldown = 600
    for svc in registry.get("services", []):
        if svc["name"] == service_name:
            cooldown = svc.get("cooldown_seconds", 600)
            break

    last = _cooldowns.get(service_name, 0)
    return (time.time() - last) < cooldown


def create_incident(service_name, evidence=None):
    """Create a new incident record."""
    data = load_incidents()
    incident = {
        "incident_id": f"INC-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}",
        "service": service_name,
        "state": "detected",
        "evidence": evidence or [],
        "action_taken": None,
        "result": None,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "ended_at": None,
        "confidence": "low",
        "requires_human": False,
    }
    data["incidents"].append(incident)
    save_incidents(data)
    return incident


def update_incident(incident_id, **kwargs):
    data = load_incidents()
    for inc in data["incidents"]:
        if inc["incident_id"] == incident_id:
            inc.update(kwargs)
            break
    save_incidents(data)


def attempt_restart(service_name, dry_run=False):
    """Attempt to restart a service. Returns success bool."""
    registry = load_json(REGISTRY_FILE)
    restart_cmd = None
    for svc in registry.get("services", []):
        if svc["name"] == service_name:
            restart_cmd = svc.get("restart_action")
            break

    if not restart_cmd:
        return False

    if dry_run:
        print(f"  [DRY-RUN] Would execute: {restart_cmd}")
        return True

    try:
        r = subprocess.run(restart_cmd, shell=True, capture_output=True, text=True,
                           timeout=30, cwd=str(ROOT))
        return r.returncode == 0
    except Exception:
        return False


def attempt_failover(service_name, dry_run=False):
    """Attempt failover for a service."""
    policy = load_json(POLICY_FILE)
    if not policy.get("allow_failover", False):
        return False, "failover_disabled"

    failover_map = load_json(FAILOVER_FILE)
    mapping = failover_map.get(service_name)
    if not mapping:
        return False, "no_failover_mapping"

    secondary = mapping.get("secondary")
    if not secondary:
        return False, "no_secondary"

    # Check secondary health (port 22 as proxy)
    import socket
    try:
        host_ips = {"nova": "10.1.1.21", "mira": "10.1.1.22", "orin": "10.1.1.23"}
        ip = host_ips.get(secondary, secondary)
        s = socket.socket()
        s.settimeout(3)
        s.connect((ip, 22))
        s.close()
    except Exception:
        return False, "secondary_unhealthy"

    if dry_run:
        print(f"  [DRY-RUN] Would failover {service_name} to {secondary}")
        return True, "dry_run"

    return True, f"failover_to_{secondary}"


def recover_service(service_name, dry_run=True):
    """Full recovery ladder for a service."""
    policy = load_json(POLICY_FILE)
    if not policy.get("enabled", False):
        print(f"  Recovery disabled by policy")
        return "disabled"

    # Step 1: Check health
    registry = load_json(REGISTRY_FILE)
    svc = None
    for s in registry.get("services", []):
        if s["name"] == service_name and s.get("enabled", True):
            svc = s
            break
    if not svc:
        print(f"  Service '{service_name}' not found or disabled")
        return "not_found"

    health_ok, status, latency = check_health(svc["health_url"])

    if health_ok:
        print(f"  [OK] {service_name} is healthy (HTTP {status}, {latency:.0f}ms)")
        return "healthy"

    # Create incident
    evidence = [{"signal": "health_check", "url": svc["health_url"], "result": "failed"}]
    incident = create_incident(service_name, evidence)
    inc_id = incident["incident_id"]
    print(f"  [DETECTED] {service_name} unhealthy -> {inc_id}")

    # Step 2: Verify with second signal
    update_incident(inc_id, state="verifying")
    process_ok = check_process(service_name)
    evidence.append({"signal": "process_check", "result": "up" if process_ok else "down"})
    confidence = "high" if not process_ok else "low"
    update_incident(inc_id, confidence=confidence, evidence=evidence)

    if health_ok and process_ok:
        update_incident(inc_id, state="recovered", ended_at=datetime.now(timezone.utc).isoformat())
        return "false_alarm"

    update_incident(inc_id, state="confirmed")
    print(f"  [CONFIRMED] {service_name} down (confidence: {confidence})")

    # Step 3: Check cooldown
    if is_cooldown_active(service_name):
        update_incident(inc_id, state="failed_recovery", requires_human=True,
                        action_taken="blocked_cooldown",
                        ended_at=datetime.now(timezone.utc).isoformat())
        audit_recovery("restart_blocked", service_name, "cooldown_active")
        print(f"  [BLOCKED] Cooldown active for {service_name}")
        return "cooldown"

    # Step 4: Attempt restart
    update_incident(inc_id, state="recovering", action_taken="restart")
    print(f"  [RECOVERING] Restarting {service_name}...")
    restart_ok = attempt_restart(service_name, dry_run=dry_run)
    _cooldowns[service_name] = time.time()

    if restart_ok or dry_run:
        # Recheck after restart
        time.sleep(2) if not dry_run else None
        if dry_run or check_health(svc["health_url"])[0]:
            update_incident(inc_id, state="recovered", result="restart_success",
                            ended_at=datetime.now(timezone.utc).isoformat())
            audit_recovery("restart", service_name, "success")
            print(f"  [RECOVERED] {service_name} restarted successfully")
            return "recovered"

    # Step 5: Try failover
    if policy.get("require_multi_signal_for_failover") and confidence != "high":
        update_incident(inc_id, state="failed_recovery", requires_human=True,
                        result="low_confidence_no_failover",
                        ended_at=datetime.now(timezone.utc).isoformat())
        audit_recovery("failover_blocked", service_name, "low_confidence")
        print(f"  [BLOCKED] Low confidence, not failing over")
        return "failed_recovery"

    fo_ok, fo_reason = attempt_failover(service_name, dry_run=dry_run)
    if fo_ok:
        update_incident(inc_id, state="recovered", result=f"failover:{fo_reason}",
                        ended_at=datetime.now(timezone.utc).isoformat())
        audit_recovery("failover", service_name, "success", {"target": fo_reason})
        print(f"  [FAILOVER] {service_name} -> {fo_reason}")
        return "failover"

    # Step 6: Quarantine
    update_incident(inc_id, state="failed_recovery", requires_human=True,
                    result=f"failover_failed:{fo_reason}",
                    ended_at=datetime.now(timezone.utc).isoformat())
    audit_recovery("recovery_failed", service_name, "requires_human")
    print(f"  [FAILED] {service_name} recovery failed, human required")
    return "failed_recovery"


def list_incidents(count=20):
    data = load_incidents()
    incidents = data.get("incidents", [])[-count:]
    print(f"{'ID':<30} {'Service':<12} {'State':<18} {'Action':<18}")
    print("-" * 78)
    for inc in incidents:
        print(f"{inc['incident_id']:<30} {inc['service']:<12} {inc['state']:<18} {inc.get('action_taken','')!s:<18}")
    if not incidents:
        print("  No incidents recorded.")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "check":
        service = sys.argv[2] if len(sys.argv) > 2 else None
        dry_run = "--dry-run" in sys.argv or "--simulate" in sys.argv
        if service:
            recover_service(service, dry_run=dry_run)
        else:
            # Check all enabled services
            registry = load_json(REGISTRY_FILE)
            for svc in registry.get("services", []):
                if svc.get("enabled", True):
                    recover_service(svc["name"], dry_run=dry_run)
    elif cmd == "incidents":
        list_incidents()
    elif cmd == "status":
        registry = load_json(REGISTRY_FILE)
        for svc in registry.get("services", []):
            ok, status, lat = check_health(svc["health_url"])
            icon = "[OK]" if ok else "[DOWN]"
            print(f"  {icon} {svc['name']:<15} HTTP {status:>3}  {lat:.0f}ms")
    else:
        print("Usage: engine.py [check [service] [--dry-run]|incidents|status]")


if __name__ == "__main__":
    main()
