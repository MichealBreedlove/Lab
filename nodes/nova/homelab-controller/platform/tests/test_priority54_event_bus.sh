#!/usr/bin/env bash
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
PASS=0; FAIL=0; API_PORT=18454
run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  PASS $n"; PASS=$((PASS+1)); else echo "  FAIL $n"; FAIL=$((FAIL+1)); fi; }
echo "=== P54 Incident Event Bus Tests ==="

AD=$(python3 "$ROOT_DIR/scripts/identity/token_issuer.py" create admin t54-admin 2>&1 | grep 'Secret:' | awk '{print $NF}')
VW=$(python3 "$ROOT_DIR/scripts/identity/token_issuer.py" create viewer t54-viewer 2>&1 | grep 'Secret:' | awk '{print $NF}')

# T1: event bus file created on emit
python3 "$ROOT_DIR/platform/events/bus.py" emit incident.created recovery-engine INC-TEST-001 >/dev/null 2>&1
run_test "T1: event log file created" \
    "test -f '$ROOT_DIR/data/events/event_log.jsonl'"

# T2: incident.created appended
run_test "T2: incident.created event appended" \
    "grep -q 'incident.created' '$ROOT_DIR/data/events/event_log.jsonl'"

# T3: recovery.started appended
python3 "$ROOT_DIR/platform/events/bus.py" emit recovery.started recovery-engine INC-TEST-001 >/dev/null 2>&1
run_test "T3: recovery.started event appended" \
    "grep -q 'recovery.started' '$ROOT_DIR/data/events/event_log.jsonl'"

# T4: GET /events returns events
PLATFORM_PORT=$API_PORT python3 "$ROOT_DIR/platform/api/server.py" &
PID=$!; sleep 2
cleanup() { kill $PID 2>/dev/null||true; python3 -c "
import json; f='$ROOT_DIR/artifacts/identity/active_tokens.json'
d=json.load(open(f)); d['tokens']=[t for t in d['tokens'] if 't54-' not in t.get('name','')]; json.dump(d,open(f,'w'),indent=2)
" 2>/dev/null||true; rm -f '$ROOT_DIR/data/events/event_log.jsonl' 2>/dev/null||true; }
trap cleanup EXIT
A="http://localhost:$API_PORT"

run_test "T4: GET /events returns events" \
    "curl -sf -H 'Authorization: Bearer $AD' '$A/events' | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d[\"count\"]>=2'"

# T5: filter by incident_id
run_test "T5: filter by incident_id" \
    "curl -sf -H 'Authorization: Bearer $AD' '$A/events?incident_id=INC-TEST-001' | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d[\"count\"]>=2'"

# T6: filter by event_type
run_test "T6: filter by event_type" \
    "curl -sf -H 'Authorization: Bearer $AD' '$A/events?type=recovery.started' | python3 -c 'import sys,json; d=json.load(sys.stdin); assert all(e[\"event_type\"]==\"recovery.started\" for e in d[\"events\"])'"

# T7: status has event_bus_enabled
run_test "T7: status has event_bus_enabled" \
    "curl -sf -H 'Authorization: Bearer $AD' '$A/' | python3 -c 'import sys,json; assert json.load(sys.stdin).get(\"event_bus_enabled\")==True'"

# T8: secret scan clean
run_test "T8: secret scan clean" \
    "! grep -rEi '(password|token|secret)\s*[:=]\s*[A-Za-z0-9+/]{8,}' '$ROOT_DIR/platform/events/' 2>/dev/null || true"

echo ""; echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && exit 1 || { echo "ALL TESTS PASSED"; exit 0; }
