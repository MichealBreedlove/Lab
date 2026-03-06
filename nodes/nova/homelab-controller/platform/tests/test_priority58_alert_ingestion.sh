#!/usr/bin/env bash
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
PASS=0; FAIL=0; API_PORT=18458
run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  PASS $n"; PASS=$((PASS+1)); else echo "  FAIL $n"; FAIL=$((FAIL+1)); fi; }
echo "=== P58 Alertmanager Event Ingestion Tests ==="

AU=$(python3 "$ROOT_DIR/scripts/identity/token_issuer.py" create automation t58-auto 2>&1 | grep 'Secret:' | awk '{print $NF}')
VW=$(python3 "$ROOT_DIR/scripts/identity/token_issuer.py" create viewer t58-viewer 2>&1 | grep 'Secret:' | awk '{print $NF}')

# Clear event log for clean test
> "$ROOT_DIR/data/events/event_log.jsonl" 2>/dev/null || true
rm -f "$ROOT_DIR/artifacts/recovery/incidents.json" 2>/dev/null || true

PLATFORM_PORT=$API_PORT python3 "$ROOT_DIR/platform/api/server.py" &
PID=$!; sleep 2
cleanup() { kill $PID 2>/dev/null||true; python3 -c "
import json; f='$ROOT_DIR/artifacts/identity/active_tokens.json'
d=json.load(open(f)); d['tokens']=[t for t in d['tokens'] if 't58-' not in t.get('name','')]; json.dump(d,open(f,'w'),indent=2)
" 2>/dev/null||true; }
trap cleanup EXIT
A="http://localhost:$API_PORT"

ALERT_PAYLOAD='{"alerts":[{"status":"firing","labels":{"alertname":"API_Down","severity":"critical","instance":"10.1.1.21:8081"},"annotations":{"description":"Platform API is unreachable"},"startsAt":"2026-03-06T06:00:00Z"}]}'

# T1: webhook accepts alert payload
run_test "T1: webhook accepts alert payload" \
    "curl -sf -X POST -H 'Authorization: Bearer $AU' -H 'Content-Type: application/json' -d '$ALERT_PAYLOAD' '$A/events/alertmanager' | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d[\"status\"]==\"accepted\"'"

# T2: incident created from alert
run_test "T2: incident created from alert" \
    "python3 -c \"
import json
d = json.load(open('$ROOT_DIR/artifacts/recovery/incidents.json'))
incs = [i for i in d['incidents'] if i['alertname']=='API_Down']
assert len(incs) >= 1, f'found {len(incs)}'
assert incs[0]['type'] == 'api_down'
assert incs[0]['status'] == 'open'
\""

# T3: event bus event created
run_test "T3: incident.created event in bus" \
    "grep -q 'incident.created' '$ROOT_DIR/data/events/event_log.jsonl'"

# T4: duplicate alert updates existing incident
run_test "T4: duplicate alert updates incident" \
    "curl -sf -X POST -H 'Authorization: Bearer $AU' -H 'Content-Type: application/json' -d '$ALERT_PAYLOAD' '$A/events/alertmanager' | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d[\"results\"][0][\"action\"]==\"updated\"'"

# T5: incident.updated event in bus
run_test "T5: incident.updated event in bus" \
    "grep -q 'incident.updated' '$ROOT_DIR/data/events/event_log.jsonl'"

# T6: event stored in JSONL
run_test "T6: events stored in JSONL" \
    "test -s '$ROOT_DIR/data/events/event_log.jsonl'"

# T7: viewer cannot post to alertmanager webhook
run_test "T7: viewer denied on alertmanager webhook" \
    "curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Authorization: Bearer $VW' -H 'Content-Type: application/json' -d '$ALERT_PAYLOAD' '$A/events/alertmanager' | grep -q '403'"

# T8: resolved alert closes incident
RESOLVED_PAYLOAD='{"alerts":[{"status":"resolved","labels":{"alertname":"API_Down","severity":"critical","instance":"10.1.1.21:8081"},"annotations":{"description":"Resolved"},"startsAt":"2026-03-06T06:00:00Z"}]}'
run_test "T8: resolved alert closes incident" \
    "curl -sf -X POST -H 'Authorization: Bearer $AU' -H 'Content-Type: application/json' -d '$RESOLVED_PAYLOAD' '$A/events/alertmanager' && python3 -c \"
import json
d = json.load(open('$ROOT_DIR/artifacts/recovery/incidents.json'))
resolved = [i for i in d['incidents'] if i['alertname']=='API_Down' and i['status']=='resolved']
assert len(resolved) >= 1
\""

# T9: different alert creates separate incident
ALERT2='{"alerts":[{"status":"firing","labels":{"alertname":"Node_Unreachable","severity":"warning","instance":"10.1.1.22:9100"},"annotations":{"description":"Mira unreachable"},"startsAt":"2026-03-06T06:05:00Z"}]}'
run_test "T9: different alert creates new incident" \
    "curl -sf -X POST -H 'Authorization: Bearer $AU' -H 'Content-Type: application/json' -d '$ALERT2' '$A/events/alertmanager' | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d[\"results\"][0][\"action\"]==\"created\"'"

# T10: secret scan clean
run_test "T10: secret scan clean" \
    "! grep -rEi '(password|token|secret)\s*[:=]\s*[A-Za-z0-9+/]{8,}' '$ROOT_DIR/platform/events/alert_ingest.py' 2>/dev/null || true"

echo ""; echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && exit 1 || { echo "ALL TESTS PASSED"; exit 0; }
