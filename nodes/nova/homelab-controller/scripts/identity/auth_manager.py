#!/usr/bin/env python3
"""Auth manager — checks authorization for control plane actions."""
import ipaddress
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
POLICY_FILE = ROOT / "config" / "identity_policy.json"

# Import siblings
sys.path.insert(0, str(Path(__file__).parent))
from token_issuer import validate_token, load_policy
from audit_log import append_event
from session_logger import log_session


def check_subnet(ip_str):
    """Check if IP is in a trusted subnet."""
    policy = load_policy()
    try:
        ip = ipaddress.ip_address(ip_str)
        for subnet in policy.get("trusted_subnets", []):
            if ip in ipaddress.ip_network(subnet):
                return True
    except ValueError:
        pass
    return False


def authorize(token_secret=None, action="", source_ip="", user="anonymous"):
    """Check if a request is authorized. Returns (allowed, role, reason)."""
    policy = load_policy()

    # Check subnet
    if source_ip and not check_subnet(source_ip):
        append_event("auth_denied", actor=user, target=action, result="subnet_rejected")
        log_session(user=user, command=action, result="denied:subnet", source_ip=source_ip)
        return False, None, f"IP {source_ip} not in trusted subnet"

    # Check token
    if token_secret:
        result = validate_token(token_secret)
        if not result:
            append_event("auth_denied", actor=user, target=action, result="invalid_token")
            log_session(user=user, command=action, result="denied:token", source_ip=source_ip)
            return False, None, "Invalid or expired token"

        role = result["role"]
        token_id = result["token_id"]
        user = result.get("name", user)
    else:
        # No token — default to viewer if from trusted subnet
        role = "viewer"
        token_id = None

    # Check action permission
    allowed_actions = policy["roles"].get(role, {}).get("allowed_actions", [])
    if "*" in allowed_actions or action in allowed_actions:
        append_event("auth_granted", actor=user, target=action, result="success",
                     details={"role": role, "token_id": token_id})
        log_session(user=user, token_id=token_id, command=action,
                    result="granted", source_ip=source_ip)
        return True, role, f"Authorized as {role}"

    append_event("auth_denied", actor=user, target=action, result="insufficient_role",
                 details={"role": role, "required_action": action})
    log_session(user=user, token_id=token_id, command=action,
                result="denied:role", source_ip=source_ip)
    return False, role, f"Role '{role}' cannot perform '{action}'"


def whoami(token_secret=None, source_ip=""):
    """Return identity info for current credentials."""
    policy = load_policy()

    info = {
        "source_ip": source_ip,
        "trusted_subnet": check_subnet(source_ip) if source_ip else True,
        "role": "anonymous",
        "token_id": None,
        "name": None,
    }

    if token_secret:
        result = validate_token(token_secret)
        if result:
            info["role"] = result["role"]
            info["token_id"] = result["token_id"]
            info["name"] = result["name"]
        else:
            info["role"] = "invalid"

    return info


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "whoami"

    if cmd == "check":
        action = sys.argv[2] if len(sys.argv) > 2 else ""
        token = sys.argv[3] if len(sys.argv) > 3 else ""
        ip = sys.argv[4] if len(sys.argv) > 4 else "127.0.0.1"
        allowed, role, reason = authorize(token_secret=token, action=action, source_ip=ip)
        status = "ALLOWED" if allowed else "DENIED"
        print(f"[{status}] {reason}")
    elif cmd == "whoami":
        token = sys.argv[2] if len(sys.argv) > 2 else ""
        info = whoami(token_secret=token, source_ip="127.0.0.1")
        for k, v in info.items():
            print(f"  {k}: {v}")
    elif cmd == "test":
        # Quick self-test
        ok, _, reason = authorize(action="drift:status", source_ip="10.1.1.21")
        print(f"  Viewer access to drift:status: {'OK' if ok else 'FAIL'} ({reason})")
        ok, _, reason = authorize(action="auth:whoami", source_ip="10.1.1.21")
        print(f"  Viewer access to auth:whoami: {'OK' if ok else 'FAIL'} ({reason})")
        ok, _, reason = authorize(action="drift:run", source_ip="10.1.1.21")
        print(f"  Viewer access to drift:run: {'OK' if not ok else 'UNEXPECTED'} ({reason})")
    else:
        print("Usage: auth_manager.py [check <action> <token> <ip>|whoami <token>|test]")


if __name__ == "__main__":
    main()
