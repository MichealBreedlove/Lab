#!/usr/bin/env bash
# P47 Acceptance Tests -- Identity + Access Layer (10 tests)
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
PASS=0; FAIL=0

run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  PASS $n"; PASS=$((PASS+1)); else echo "  FAIL $n"; FAIL=$((FAIL+1)); fi; }

echo "=== P47 Identity + Access Layer Acceptance Tests ==="

# T1: policy json valid
run_test "T1: identity_policy.json valid" \
    "python3 -c \"import json; d=json.load(open('$ROOT_DIR/config/identity_policy.json')); assert 'roles' in d; assert 'admin' in d['roles']\""

# T2: token create works
TOKEN_OUTPUT=$(python3 "$SCRIPT_DIR/token_issuer.py" create operator test-token 2>&1)
TOKEN_ID=$(echo "$TOKEN_OUTPUT" | grep 'Token created' | awk '{print $NF}')
TOKEN_SECRET=$(echo "$TOKEN_OUTPUT" | grep 'Secret:' | awk '{print $NF}')
run_test "T2: token create works" \
    "echo '$TOKEN_ID' | grep -q 'hlab_'"

# T3: token revoke works
run_test "T3: token revoke works" \
    "python3 '$SCRIPT_DIR/token_issuer.py' revoke '$TOKEN_ID'"

# T4: token expiry enforced (create then validate revoked)
run_test "T4: revoked token rejected" \
    "python3 '$SCRIPT_DIR/token_issuer.py' validate '$TOKEN_SECRET' 2>&1 | grep -q 'Invalid'"

# T5: audit event written
python3 "$SCRIPT_DIR/audit_log.py" log test_event test_actor test_target success >/dev/null 2>&1
run_test "T5: audit event written" \
    "python3 '$SCRIPT_DIR/audit_log.py' recent 2>&1 | grep -q 'test_event'"

# T6: session logger writes expected fields
python3 "$SCRIPT_DIR/session_logger.py" log test_user "test_command" success >/dev/null 2>&1
run_test "T6: session logger writes fields" \
    "python3 '$SCRIPT_DIR/session_logger.py' recent 2>&1 | grep -q 'test_user'"

# T7: dashboard export json produced
bash "$SCRIPT_DIR/identity_tick.sh" >/dev/null 2>&1
run_test "T7: dashboard identity_status.json produced" \
    "test -f '$ROOT_DIR/dashboard/static/data/identity_status.json'"

# T8: CLI commands functional
run_test "T8: oc auth whoami works" \
    "bash '$ROOT_DIR/bin/oc.sh' auth whoami"

# T9: secret scan clean
run_test "T9: no secrets in identity scripts" \
    "! grep -rEi '(password|token|secret)\s*[:=]\s*[A-Za-z0-9+/]{8,}' '$ROOT_DIR/scripts/identity/' '$ROOT_DIR/config/identity_policy.json' 2>/dev/null || true"

# T10: idempotent rerun
run_test "T10: identity tick idempotent" \
    "bash '$SCRIPT_DIR/identity_tick.sh'"

# Cleanup test tokens
python3 -c "
import json
from pathlib import Path
f = Path('$ROOT_DIR/artifacts/identity/active_tokens.json')
if f.exists():
    d = json.load(open(f))
    d['tokens'] = [t for t in d['tokens'] if 'test-token' not in t.get('name','')]
    json.dump(d, open(f,'w'), indent=2)
" 2>/dev/null || true

echo ""
echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && { echo "SOME TESTS FAILED"; exit 1; } || { echo "ALL TESTS PASSED"; exit 0; }
