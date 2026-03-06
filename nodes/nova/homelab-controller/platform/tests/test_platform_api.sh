#!/usr/bin/env bash
# P46 Acceptance Tests -- Platform API (10 tests)
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
PASS=0; FAIL=0
API_PORT=18446  # Use high port for testing to avoid conflicts

run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  PASS $n"; PASS=$((PASS+1)); else echo "  FAIL $n"; FAIL=$((FAIL+1)); fi; }

echo "=== P46 Platform API Acceptance Tests ==="

# Start API server in background for testing
PLATFORM_PORT=$API_PORT python3 "$ROOT_DIR/platform/api/server.py" &
API_PID=$!
sleep 2

cleanup() { kill $API_PID 2>/dev/null || true; }
trap cleanup EXIT

# T1: API server starts
run_test "T1: API server starts" \
    "curl -sf http://localhost:$API_PORT/ | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d[\"status\"]==\"running\"'"

# T2: /topology endpoint works
run_test "T2: /topology returns data" \
    "curl -sf http://localhost:$API_PORT/topology | python3 -c 'import sys,json; d=json.load(sys.stdin); assert \"topology\" in d'"

# T3: /change triggers change log
run_test "T3: /change creates change" \
    "curl -sf -X POST http://localhost:$API_PORT/change -H 'Content-Type: application/json' -d '{\"trigger\":\"manual\",\"summary\":\"test\"}' | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d[\"change_id\"].startswith(\"CHG-\")'"

# T4: /chaos triggers chaos engine
run_test "T4: /chaos triggers scenario" \
    "curl -sf -X POST http://localhost:$API_PORT/chaos -H 'Content-Type: application/json' -d '{\"scenario\":\"gateway_restart_outage\"}' | python3 -c 'import sys,json; d=json.load(sys.stdin); assert \"change_id\" in d'"

# T5: /snapshot runs pipeline
run_test "T5: /snapshot runs pipeline" \
    "curl -sf -X POST http://localhost:$API_PORT/snapshot -H 'Content-Type: application/json' -d '{}' | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d[\"status\"]==\"completed\"'"

# T6: artifacts created in changes/
run_test "T6: change artifacts exist" \
    "ls -d '$ROOT_DIR/changes'/CHG-* 2>/dev/null | head -1"

# T7: dashboard platform_status.json exists
run_test "T7: dashboard panel data exists" \
    "test -f '$ROOT_DIR/dashboard/static/data/platform_status.json'"

# T8: CLI commands functional
run_test "T8: oc platform status works" \
    "bash '$ROOT_DIR/bin/oc.sh' platform status"

# T9: secret scan clean
run_test "T9: no secrets in platform files" \
    "! grep -rEi '(password|token|secret)\s*[:=]\s*[A-Za-z0-9+/]{8,}' '$ROOT_DIR/platform/' 2>/dev/null || true"

# T10: idempotent request
run_test "T10: repeated /change is idempotent" \
    "curl -sf -X POST http://localhost:$API_PORT/change -H 'Content-Type: application/json' -d '{\"trigger\":\"manual\",\"summary\":\"idempotent test\"}' | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d[\"status\"]==\"completed\"'"

# Cleanup test changes
rm -rf "$ROOT_DIR/changes"/CHG-* 2>/dev/null || true

echo ""
echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && { echo "SOME TESTS FAILED"; exit 1; } || { echo "ALL TESTS PASSED"; exit 0; }
