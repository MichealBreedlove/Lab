#!/usr/bin/env python3
"""Token issuer for homelab control plane identity layer."""
import hashlib
import json
import os
import secrets
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TOKENS_FILE = ROOT / "artifacts" / "identity" / "active_tokens.json"
POLICY_FILE = ROOT / "config" / "identity_policy.json"


def load_policy():
    with open(POLICY_FILE) as f:
        return json.load(f)


def load_tokens():
    if TOKENS_FILE.exists():
        with open(TOKENS_FILE) as f:
            return json.load(f)
    return {"tokens": []}


def save_tokens(data):
    TOKENS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKENS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def create_token(role="operator", name="", ttl_hours=None):
    """Create a new access token."""
    policy = load_policy()
    roles = policy["roles"]

    if role not in roles:
        print(f"[ERROR] Invalid role: {role}. Valid: {', '.join(roles.keys())}")
        return None

    if ttl_hours is None:
        ttl_hours = policy["token_config"]["ttl_hours"]

    prefix = policy["token_config"]["prefix"]
    raw = secrets.token_hex(24)
    token_id = f"{prefix}{raw[:8]}"
    token_hash = hashlib.sha256(raw.encode()).hexdigest()

    now = datetime.now(timezone.utc)
    expires = now + timedelta(hours=ttl_hours)

    record = {
        "token_id": token_id,
        "token_hash": token_hash,
        "role": role,
        "name": name or f"{role}-token",
        "created_at": now.isoformat(),
        "expires_at": expires.isoformat(),
        "revoked": False,
        "last_used": None,
    }

    data = load_tokens()
    data["tokens"].append(record)
    save_tokens(data)

    print(f"[OK] Token created: {token_id}")
    print(f"     Role: {role}")
    print(f"     Expires: {expires.isoformat()}")
    print(f"     Secret: {prefix}{raw}")
    return token_id


def revoke_token(token_id, reason=""):
    """Revoke a token by ID."""
    data = load_tokens()
    found = False
    for t in data["tokens"]:
        if t["token_id"] == token_id:
            t["revoked"] = True
            t["revoked_at"] = datetime.now(timezone.utc).isoformat()
            if reason:
                t["revoked_reason"] = reason
            found = True
            break

    if found:
        save_tokens(data)
        print(f"[OK] Token revoked: {token_id}")
    else:
        print(f"[ERROR] Token not found: {token_id}")
    return found


def list_tokens(show_expired=False):
    """List active tokens."""
    data = load_tokens()
    now = datetime.now(timezone.utc)
    active = 0
    expired = 0
    revoked = 0

    print(f"{'ID':<20} {'Role':<12} {'Name':<20} {'Status':<10} {'Expires':<25}")
    print("-" * 87)

    for t in data["tokens"]:
        exp = datetime.fromisoformat(t["expires_at"])
        if t["revoked"]:
            status = "REVOKED"
            revoked += 1
        elif exp < now:
            status = "EXPIRED"
            expired += 1
        else:
            status = "ACTIVE"
            active += 1

        if show_expired or status == "ACTIVE":
            print(f"{t['token_id']:<20} {t['role']:<12} {t['name']:<20} {status:<10} {t['expires_at'][:19]}")

    print(f"\nActive: {active} | Expired: {expired} | Revoked: {revoked}")
    return active


def validate_token(token_secret):
    """Validate a token and return its role, or None if invalid."""
    data = load_tokens()
    policy = load_policy()
    prefix = policy["token_config"]["prefix"]
    now = datetime.now(timezone.utc)

    if not token_secret.startswith(prefix):
        return None

    raw = token_secret[len(prefix):]
    token_hash = hashlib.sha256(raw.encode()).hexdigest()

    for t in data["tokens"]:
        if t["token_hash"] == token_hash:
            if t["revoked"]:
                return None
            exp = datetime.fromisoformat(t["expires_at"])
            if exp < now:
                return None
            t["last_used"] = now.isoformat()
            save_tokens(data)
            return {"token_id": t["token_id"], "role": t["role"], "name": t["name"]}

    return None


def cleanup_expired():
    """Remove expired/revoked tokens older than retention period."""
    policy = load_policy()
    retention = timedelta(days=policy["audit"]["retention_days"])
    now = datetime.now(timezone.utc)
    data = load_tokens()

    kept = []
    removed = 0
    for t in data["tokens"]:
        created = datetime.fromisoformat(t["created_at"])
        if (t["revoked"] or datetime.fromisoformat(t["expires_at"]) < now) and (now - created) > retention:
            removed += 1
        else:
            kept.append(t)

    data["tokens"] = kept
    save_tokens(data)
    if removed:
        print(f"[OK] Cleaned up {removed} expired/revoked tokens")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"

    if cmd == "create":
        role = sys.argv[2] if len(sys.argv) > 2 else "operator"
        name = sys.argv[3] if len(sys.argv) > 3 else ""
        create_token(role=role, name=name)
    elif cmd == "revoke":
        token_id = sys.argv[2] if len(sys.argv) > 2 else ""
        reason = ""
        if "--reason" in sys.argv:
            idx = sys.argv.index("--reason")
            reason = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
        if not token_id:
            print("[ERROR] Usage: token_issuer.py revoke <token_id> [--reason <reason>]")
        else:
            revoke_token(token_id, reason=reason)
    elif cmd == "list":
        show_all = "--all" in sys.argv
        list_tokens(show_expired=show_all)
    elif cmd == "validate":
        secret = sys.argv[2] if len(sys.argv) > 2 else ""
        result = validate_token(secret)
        if result:
            print(f"[OK] Valid token: {result['token_id']} (role: {result['role']})")
        else:
            print("[FAIL] Invalid or expired token")
    elif cmd == "cleanup":
        cleanup_expired()
    else:
        print("Usage: token_issuer.py [create|revoke|list|validate|cleanup]")


if __name__ == "__main__":
    main()
