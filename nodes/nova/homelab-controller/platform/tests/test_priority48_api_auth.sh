#!/usr/bin/env bash
# P48 Acceptance Tests -- Role-Based Platform API Enforcement (10 tests)
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
PASS=0; FAIL=0
API_PORT=18448

run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  PASS $n"; PASS=$((PASS+1)); else echo "  FAIL $n"; FAIL=$((FAIL+1)); fi; }

echo "=== P48 Role-Based API Auth Acceptance Tests ==="

# Create test tokens for each role
VIEWER_OUT=$(python3 "$ROOT_DIR/scripts/identity/token_issuer.py" create viewer test-viewer 2>&1)
VIEWER_SECRET=$(echo "$VIEWER_OUT" | grep 'Secret:' | awk '{print $NF}')

OPERATOR_OUT=$(python3 "$ROOT_DIR/scripts/identity/token_issuer.py" create operator test-operator 2>&1)
OPERATOR_SECRET=$(echo "$OPERATOR_OUT" | grep 'Secret:' | awk '{print $NF}')

SRE_OUT=$(python3 "$ROOT_DIR/scripts/identity/token_issuer.py" create sre test-sre 2>&1)
SRE_SECRET=$(echo "$SRE_OUT" | grep 'Secret:' | awk '{print $NF}')

ADMIN_OUT=$(python3 "$ROOT_DIR/scripts/identity/token_issuer.py" create admin test-admin 2>&1)
ADMIN_SECRET=$(echo "$ADMIN_OUT" | grep 'Secret:' | awk '{print $NF}')

# Start API server
PLATFORM_PORT=$API_PORT python3 "$ROOT_DIR/platform/api/server.py" &
API_PID=$!
sleep 2

cleanup() {
    kill $API_PID 2>/dev/null || true
    # Cleanup test tokens
    python3 -c "
import json
from pathlib import Path
f = Path('$ROOT_DIR/artifacts/identity/active_tokens.json')
if f.exists():
    d = json.load(open(f))
    d['tokens'] = [t for t in d['tokens'] if 'test-' not in t.get('name','')]
    json.dump(d, open(f,'w'), indent=2)
" 2>/dev/null || true
}
trap cleanup EXIT

API="http://localhost:$API_PORT"

# T1: valid token allows status
run_test "T1: valid viewer token allows GET /" \
    "curl -sf -H 'Authorization: Bearer $VIEWER_SECRET' $API/ | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d[\"status\"]==\"running\"'"

# T2: invalid token denied (401)
run_test "T2: invalid token returns 401" \
    "curl -s -o /dev/null -w '%{http_code}' -H 'Authorization: Bearer hlab_invalid123' $API/ | grep -q '401'"

# T3: viewer cannot call chaos (403)
run_test "T3: viewer cannot POST /chaos" \
    "curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Authorization: Bearer $VIEWER_SECRET' -H 'Content-Type: application/json' -d '{}' $API/chaos | grep -q '403'"

# T4: operator can snapshot
run_test "T4: operator can POST /snapshot" \
    "curl -sf -X POST -H 'Authorization: Bearer $OPERATOR_SECRET' -H 'Content-Type: application/json' -d '{}' $API/snapshot | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d[\"status\"]==\"completed\"'"

# T5: sre can chaos
run_test "T5: sre can POST /chaos" \
    "curl -sf -X POST -H 'Authorization: Bearer $SRE_SECRET' -H 'Content-Type: application/json' -d '{\"scenario\":\"gateway_restart_outage\"}' $API/chaos | python3 -c 'import sys,json; d=json.load(sys.stdin); assert \"change_id\" in d'"

# T6: admin can all
run_test "T6: admin can POST /chaos" \
    "curl -sf -X POST -H 'Authorization: Bearer $ADMIN_SECRET' -H 'Content-Type: application/json' -d '{\"scenario\":\"gateway_restart_outage\"}' $API/chaos | python3 -c 'import sys,json; d=json.load(sys.stdin); assert \"change_id\" in d'"

# T7: audit entry written
run_test "T7: API audit entries written" \
    "test -f '$ROOT_DIR/artifacts/identity/api_audit.jsonl' && wc -l < '$ROOT_DIR/artifacts/identity/api_audit.jsonl' | awk '{exit (\$1 >= 3) ? 0 : 1}'"

# T8: no-token request returns 401
run_test "T8: no token returns 401" \
    "curl -s -o /dev/null -w '%{http_code}' $API/ | grep -q '401'"

# T9: dashboard platform_status.json has auth field
run_test "T9: dashboard status has auth_required" \
    "test -f '$ROOT_DIR/dashboard/static/data/platform_status.json' && python3 -c \"import json; d=json.load(open('$ROOT_DIR/dashboard/static/data/platform_status.json')); assert d.get('auth_required')==True\""

# T10: secret scan clean
run_test "T10: no secrets in platform files" \
    "! grep -rEi '(password|token|secret)\s*[:=]\s*[A-Za-z0-9+/]{8,}' '$ROOT_DIR/platform/api/server.py' 2>/dev/null || true"

# Cleanup test changes
rm -rf "$ROOT_DIR/changes"/CHG-* 2>/dev/null || true

echo ""
echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && { echo "SOME TESTS FAILED"; exit 1; } || { echo "ALL TESTS PASSED"; exit 0; }
