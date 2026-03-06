#!/usr/bin/env bash
# Identity tick - cleanup expired tokens, generate audit summary, export dashboard data
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."

echo "[INFO] Identity tick starting"

# Cleanup expired tokens
python3 "$SCRIPT_DIR/token_issuer.py" cleanup 2>&1

# Generate audit summary
python3 "$SCRIPT_DIR/audit_log.py" summary 2>&1

# Export dashboard data
python3 -c "
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path('$ROOT_DIR')
tokens_file = ROOT / 'artifacts' / 'identity' / 'active_tokens.json'
audit_file = ROOT / 'artifacts' / 'identity' / 'audit_latest.json'
dash_dir = ROOT / 'dashboard' / 'static' / 'data'
dash_dir.mkdir(parents=True, exist_ok=True)

active = 0
if tokens_file.exists():
    data = json.load(open(tokens_file))
    now = datetime.now(timezone.utc)
    for t in data.get('tokens', []):
        if not t.get('revoked') and datetime.fromisoformat(t['expires_at']) > now:
            active += 1

audit = {}
if audit_file.exists():
    audit = json.load(open(audit_file))

dash = {
    'timestamp': datetime.now(timezone.utc).isoformat(),
    'active_tokens': active,
    'last_audit_event': audit.get('latest_event'),
    'failed_auth_count': audit.get('failed_events', 0),
    'total_audit_events': audit.get('total_events', 0),
    'break_glass_active': False,
}
with open(dash_dir / 'identity_status.json', 'w') as f:
    json.dump(dash, f, indent=2)
print('[OK] Dashboard identity data exported')
" 2>&1

echo "[INFO] Identity tick complete"
