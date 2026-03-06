#!/usr/bin/env bash
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
PASS=0; FAIL=0; API_PORT=18449
run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  PASS $n"; PASS=$((PASS+1)); else echo "  FAIL $n"; FAIL=$((FAIL+1)); fi; }
echo "=== P49 Rate Limiting Acceptance Tests ==="

# Create tokens
VW=$(python3 "$ROOT_DIR/scripts/identity/token_issuer.py" create viewer t49-viewer 2>&1 | grep 'Secret:' | awk '{print $NF}')
OP=$(python3 "$ROOT_DIR/scripts/identity/token_issuer.py" create operator t49-operator 2>&1 | grep 'Secret:' | awk '{print $NF}')
SR=$(python3 "$ROOT_DIR/scripts/identity/token_issuer.py" create sre t49-sre 2>&1 | grep 'Secret:' | awk '{print $NF}')
AD=$(python3 "$ROOT_DIR/scripts/identity/token_issuer.py" create admin t49-admin 2>&1 | grep 'Secret:' | awk '{print $NF}')

# Override policy with low limits for testing
cat > /tmp/rl_test_policy.json << 'EOF'
{"enabled":true,"window_seconds":60,"limits":{"viewer":3,"operator":2,"sre":2,"admin":0}}
EOF
cp "$ROOT_DIR/config/rate_limit_policy.json" /tmp/rl_orig.json
cp /tmp/rl_test_policy.json "$ROOT_DIR/config/rate_limit_policy.json"

PLATFORM_PORT=$API_PORT python3 "$ROOT_DIR/platform/api/server.py" &
PID=$!; sleep 2
cleanup() { kill $PID 2>/dev/null||true; cp /tmp/rl_orig.json "$ROOT_DIR/config/rate_limit_policy.json"; python3 -c "
import json; f='$ROOT_DIR/artifacts/identity/active_tokens.json'
d=json.load(open(f)); d['tokens']=[t for t in d['tokens'] if 't49-' not in t.get('name','')]; json.dump(d,open(f,'w'),indent=2)
" 2>/dev/null||true; }
trap cleanup EXIT
A="http://localhost:$API_PORT"

# T1: viewer can make 3 requests
for i in 1 2 3; do curl -sf -H "Authorization: Bearer $VW" "$A/" >/dev/null; done
run_test "T1: viewer 3 requests allowed" "true"

# T2: 4th request returns 429
run_test "T2: viewer 4th request returns 429" \
    "curl -s -o /dev/null -w '%{http_code}' -H 'Authorization: Bearer $VW' '$A/' | grep -q '429'"

# T3: operator limit at 2
for i in 1 2; do curl -sf -H "Authorization: Bearer $OP" "$A/" >/dev/null; done
run_test "T3: operator limit enforced" \
    "curl -s -o /dev/null -w '%{http_code}' -H 'Authorization: Bearer $OP' '$A/' | grep -q '429'"

# T4: sre limit at 2
for i in 1 2; do curl -sf -H "Authorization: Bearer $SR" "$A/" >/dev/null; done
run_test "T4: sre limit enforced" \
    "curl -s -o /dev/null -w '%{http_code}' -H 'Authorization: Bearer $SR' '$A/' | grep -q '429'"

# T5: admin unlimited
for i in $(seq 1 10); do curl -sf -H "Authorization: Bearer $AD" "$A/" >/dev/null; done
run_test "T5: admin unlimited" "curl -sf -H 'Authorization: Bearer $AD' '$A/'"

# T6: invalid token still 401 not 429
run_test "T6: invalid token returns 401 not 429" \
    "curl -s -o /dev/null -w '%{http_code}' -H 'Authorization: Bearer hlab_bad' '$A/' | grep -q '401'"

# T7: audit entry for blocked request
run_test "T7: 429 audit entry exists" \
    "grep -q '429_rate_limited' '$ROOT_DIR/artifacts/identity/api_audit.jsonl'"

# T8: status shows rate_limit_enabled
run_test "T8: status has rate_limit_enabled" \
    "curl -sf -H 'Authorization: Bearer $AD' '$A/' | python3 -c 'import sys,json; assert json.load(sys.stdin).get(\"rate_limit_enabled\")==True'"

echo ""; echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && exit 1 || { echo "ALL TESTS PASSED"; exit 0; }
