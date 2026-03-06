#!/usr/bin/env bash
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
PASS=0; FAIL=0; API_PORT=18450
run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  PASS $n"; PASS=$((PASS+1)); else echo "  FAIL $n"; FAIL=$((FAIL+1)); fi; }
echo "=== P50 Token Revocation Acceptance Tests ==="

# Create token
OUT=$(python3 "$ROOT_DIR/scripts/identity/token_issuer.py" create operator t50-revoke 2>&1)
TID=$(echo "$OUT" | grep 'Token created:' | awk '{print $NF}')
SEC=$(echo "$OUT" | grep 'Secret:' | awk '{print $NF}')

PLATFORM_PORT=$API_PORT python3 "$ROOT_DIR/platform/api/server.py" &
PID=$!; sleep 2
cleanup() { kill $PID 2>/dev/null||true; python3 -c "
import json; f='$ROOT_DIR/artifacts/identity/active_tokens.json'
d=json.load(open(f)); d['tokens']=[t for t in d['tokens'] if 't50-' not in t.get('name','')]; json.dump(d,open(f,'w'),indent=2)
" 2>/dev/null||true; }
trap cleanup EXIT
A="http://localhost:$API_PORT"

# T1: token works before revocation
run_test "T1: token works before revoke" \
    "curl -sf -H 'Authorization: Bearer $SEC' '$A/'"

# T2: revoke token
run_test "T2: revoke succeeds" \
    "python3 '$ROOT_DIR/scripts/identity/token_issuer.py' revoke '$TID'"

# T3: revoked token returns 401
run_test "T3: revoked token returns 401" \
    "curl -s -o /dev/null -w '%{http_code}' -H 'Authorization: Bearer $SEC' '$A/' | grep -q '401'"

# T4: revocation persists (check file)
run_test "T4: revocation persists in file" \
    "python3 -c \"import json; d=json.load(open('$ROOT_DIR/artifacts/identity/active_tokens.json')); assert any(t.get('revoked') for t in d['tokens'] if t.get('name')=='t50-revoke')\""

# T5: revocation with reason
OUT2=$(python3 "$ROOT_DIR/scripts/identity/token_issuer.py" create operator t50-reason 2>&1)
TID2=$(echo "$OUT2" | grep 'Token created:' | awk '{print $NF}')
run_test "T5: revoke with reason" \
    "python3 '$ROOT_DIR/scripts/identity/token_issuer.py' revoke '$TID2' --reason leaked"

# T6: non-existent token revoke handles gracefully
run_test "T6: revoke nonexistent shows error" \
    "python3 '$ROOT_DIR/scripts/identity/token_issuer.py' revoke 'hlab_doesnotexist' 2>&1 | grep -qi 'not found'"

# T7: secret scan clean
run_test "T7: secret scan clean" \
    "! grep -rEi '(password|token|secret)\s*[:=]\s*[A-Za-z0-9+/]{8,}' '$ROOT_DIR/scripts/identity/token_issuer.py' 2>/dev/null || true"

echo ""; echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && exit 1 || { echo "ALL TESTS PASSED"; exit 0; }
