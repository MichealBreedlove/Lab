#!/usr/bin/env python3
"""Service account management for homelab control plane."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SA_FILE = ROOT / "data" / "auth" / "service_accounts.json"

sys.path.insert(0, str(Path(__file__).parent))
from token_issuer import create_token, load_tokens, save_tokens

VALID_ROLES = ["viewer", "operator", "sre", "admin", "automation"]


def _load():
    SA_FILE.parent.mkdir(parents=True, exist_ok=True)
    if SA_FILE.exists():
        with open(SA_FILE) as f:
            return json.load(f)
    return {"service_accounts": []}


def _save(data):
    SA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def create_sa(name, role="operator", description=""):
    if role not in VALID_ROLES:
        print(f"[ERROR] Invalid role: {role}")
        return None
    data = _load()
    for sa in data["service_accounts"]:
        if sa["name"] == name:
            print(f"[ERROR] Service account '{name}' already exists")
            return None

    sa = {
        "name": name,
        "role": role,
        "enabled": True,
        "description": description or f"Service account: {name}",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    data["service_accounts"].append(sa)
    _save(data)
    print(f"[OK] Service account created: {name} (role: {role})")
    return sa


def list_sa():
    data = _load()
    print(f"{'Name':<20} {'Role':<12} {'Enabled':<10} {'Description':<30}")
    print("-" * 72)
    for sa in data["service_accounts"]:
        en = "YES" if sa["enabled"] else "NO"
        print(f"{sa['name']:<20} {sa['role']:<12} {en:<10} {sa.get('description','')[:30]}")
    if not data["service_accounts"]:
        print("  No service accounts.")


def set_enabled(name, enabled):
    data = _load()
    for sa in data["service_accounts"]:
        if sa["name"] == name:
            sa["enabled"] = enabled
            _save(data)
            state = "enabled" if enabled else "disabled"
            print(f"[OK] Service account '{name}' {state}")
            return True
    print(f"[ERROR] Service account '{name}' not found")
    return False


def get_sa(name):
    data = _load()
    for sa in data["service_accounts"]:
        if sa["name"] == name:
            return sa
    return None


def create_sa_token(sa_name, token_name=""):
    """Create a token bound to a service account."""
    sa = get_sa(sa_name)
    if not sa:
        print(f"[ERROR] Service account '{sa_name}' not found")
        return None
    if not sa["enabled"]:
        print(f"[ERROR] Service account '{sa_name}' is disabled")
        return None

    full_name = token_name or f"sa-{sa_name}"
    token_id = create_token(role=sa["role"], name=full_name)
    if token_id:
        # Tag the token with principal_type
        tokens_data = load_tokens()
        for t in tokens_data["tokens"]:
            if t["token_id"] == token_id:
                t["principal_type"] = "service_account"
                t["service_account"] = sa_name
                break
        save_tokens(tokens_data)
    return token_id


def is_sa_enabled(sa_name):
    """Check if a service account is enabled."""
    sa = get_sa(sa_name)
    return sa is not None and sa.get("enabled", False)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"

    if cmd == "create":
        name = sys.argv[2] if len(sys.argv) > 2 else ""
        role = "operator"
        desc = ""
        if "--role" in sys.argv:
            idx = sys.argv.index("--role")
            role = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "operator"
        if "--desc" in sys.argv:
            idx = sys.argv.index("--desc")
            desc = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
        if not name:
            print("[ERROR] Usage: service_accounts.py create <name> --role <role>")
        else:
            create_sa(name, role=role, description=desc)
    elif cmd == "list":
        list_sa()
    elif cmd == "disable":
        name = sys.argv[2] if len(sys.argv) > 2 else ""
        set_enabled(name, False)
    elif cmd == "enable":
        name = sys.argv[2] if len(sys.argv) > 2 else ""
        set_enabled(name, True)
    elif cmd == "token":
        subcmd = sys.argv[2] if len(sys.argv) > 2 else ""
        if subcmd == "create":
            sa_name = sys.argv[3] if len(sys.argv) > 3 else ""
            tk_name = sys.argv[4] if len(sys.argv) > 4 else ""
            if not sa_name:
                print("[ERROR] Usage: service_accounts.py token create <sa-name> [token-name]")
            else:
                create_sa_token(sa_name, tk_name)
        else:
            print("Usage: service_accounts.py token create <sa-name> [token-name]")
    else:
        print("Usage: service_accounts.py [create|list|disable|enable|token create]")


if __name__ == "__main__":
    main()
