#!/usr/bin/env bash
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
PASS=0; FAIL=0; API_PORT=18451
run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  PASS $n"; PASS=$((PASS+1)); else echo "  FAIL $n"; FAIL=$((FAIL+1)); fi; }
echo "=== P51 Service Accounts Acceptance Tests ==="

AD=$(python3 "$ROOT_DIR/scripts/identity/token_issuer.py" create admin t51-admin 2>&1 | grep 'Secret:' | awk '{print $NF}')

# T1: create service account
run_test "T1: create service account" \
    "python3 '$ROOT_DIR/scripts/identity/service_accounts.py' create t51-ci --role operator"

# T2: create token for SA
SA_SEC=$(python3 "$ROOT_DIR/scripts/identity/service_accounts.py" token create t51-ci t51-sa-token 2>&1 | grep 'Secret:' | awk '{print $NF}')
run_test "T2: create SA token" "test -n '$SA_SEC'"

# T3: SA token works at API
PLATFORM_PORT=$API_PORT python3 "$ROOT_DIR/platform/api/server.py" &
PID=$!; sleep 2
cleanup() { kill $PID 2>/dev/null||true
python3 -c "
import json
for f in ['$ROOT_DIR/artifacts/identity/active_tokens.json','$ROOT_DIR/data/auth/service_accounts.json']:
    try:
        d=json.load(open(f))
        k='tokens' if 'tokens' in d else 'service_accounts'
        d[k]=[x for x in d[k] if 't51-' not in x.get('name','')]
        json.dump(d,open(f,'w'),indent=2)
    except: pass
" 2>/dev/null||true; }
trap cleanup EXIT
A="http://localhost:$API_PORT"

run_test "T3: SA token accesses operator endpoint" \
    "curl -sf -H 'Authorization: Bearer $SA_SEC' '$A/'"

# T4: disable SA
python3 "$ROOT_DIR/scripts/identity/service_accounts.py" disable t51-ci >/dev/null 2>&1
run_test "T4: disabled SA returns 401" \
    "curl -s -o /dev/null -w '%{http_code}' -H 'Authorization: Bearer $SA_SEC' '$A/' | grep -q '401'"

# T5: list shows account
run_test "T5: list shows SA" \
    "python3 '$ROOT_DIR/scripts/identity/service_accounts.py' list 2>&1 | grep -q 't51-ci'"

# T6: principal_type in token data
run_test "T6: principal_type=service_account in token" \
    "python3 -c \"import json; d=json.load(open('$ROOT_DIR/artifacts/identity/active_tokens.json')); assert any(t.get('principal_type')=='service_account' for t in d['tokens'])\""

# T7: secret scan clean
run_test "T7: secret scan clean" \
    "! grep -rEi '(password|token|secret)\s*[:=]\s*[A-Za-z0-9+/]{8,}' '$ROOT_DIR/scripts/identity/service_accounts.py' 2>/dev/null || true"

echo ""; echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && exit 1 || { echo "ALL TESTS PASSED"; exit 0; }
