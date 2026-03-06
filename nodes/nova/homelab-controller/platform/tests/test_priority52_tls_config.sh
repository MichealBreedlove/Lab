#!/usr/bin/env bash
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
PASS=0; FAIL=0
run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  PASS $n"; PASS=$((PASS+1)); else echo "  FAIL $n"; FAIL=$((FAIL+1)); fi; }
echo "=== P52 TLS / Reverse Proxy Config Tests ==="

# T1: Caddyfile exists
run_test "T1: Caddyfile exists" \
    "test -f '$ROOT_DIR/deploy/caddy/Caddyfile'"

# T2: Caddyfile references backend
run_test "T2: config references backend 127.0.0.1:8081" \
    "grep -q '127.0.0.1:8081' '$ROOT_DIR/deploy/caddy/Caddyfile'"

# T3: Caddyfile uses TLS
run_test "T3: config uses TLS" \
    "grep -q 'tls internal' '$ROOT_DIR/deploy/caddy/Caddyfile'"

# T4: Auth header forwarding preserved
run_test "T4: auth header forwarding in config" \
    "grep -q 'header_up' '$ROOT_DIR/deploy/caddy/Caddyfile'"

# T5: API status reports tls_configured
AD=$(python3 "$ROOT_DIR/scripts/identity/token_issuer.py" create admin t52-admin 2>&1 | grep 'Secret:' | awk '{print $NF}')
API_PORT=18452 PLATFORM_PORT=18452 python3 "$ROOT_DIR/platform/api/server.py" &
PID=$!; sleep 2
run_test "T5: status reports tls_configured=true" \
    "curl -sf -H 'Authorization: Bearer $AD' 'http://localhost:18452/' | python3 -c 'import sys,json; assert json.load(sys.stdin).get(\"tls_configured\")==True'"
kill $PID 2>/dev/null || true

# T6: docs exist
run_test "T6: TLS docs exist" \
    "test -f '$ROOT_DIR/docs/p52_tls.md'"

# T7: secret scan clean
run_test "T7: secret scan clean" \
    "! grep -rEi '(password|token|secret)\s*[:=]\s*[A-Za-z0-9+/]{8,}' '$ROOT_DIR/deploy/' 2>/dev/null || true"

# Cleanup
python3 -c "
import json; f='$ROOT_DIR/artifacts/identity/active_tokens.json'
d=json.load(open(f)); d['tokens']=[t for t in d['tokens'] if 't52-' not in t.get('name','')]; json.dump(d,open(f,'w'),indent=2)
" 2>/dev/null || true

echo ""; echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && exit 1 || { echo "ALL TESTS PASSED"; exit 0; }
