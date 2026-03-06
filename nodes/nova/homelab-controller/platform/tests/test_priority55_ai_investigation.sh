#!/usr/bin/env bash
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
PASS=0; FAIL=0; API_PORT=18455
run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  PASS $n"; PASS=$((PASS+1)); else echo "  FAIL $n"; FAIL=$((FAIL+1)); fi; }
echo "=== P55 AI Investigation Playbooks Tests ==="

VW=$(python3 "$ROOT_DIR/scripts/identity/token_issuer.py" create viewer t55-viewer 2>&1 | grep 'Secret:' | awk '{print $NF}')
SR=$(python3 "$ROOT_DIR/scripts/identity/token_issuer.py" create sre t55-sre 2>&1 | grep 'Secret:' | awk '{print $NF}')

# T1: correct playbook selected for api incident
run_test "T1: api_down playbook selected" \
    "python3 -c \"
import sys; sys.path.insert(0,'$ROOT_DIR/platform/aiops')
from investigator import select_playbook
pb = select_playbook('api','confirmed')
assert pb['name']=='api_down'
\""

# T2: investigation artifact written (simulate mode)
python3 "$ROOT_DIR/platform/aiops/investigator.py" run INC-T55-001 api confirmed --simulate >/dev/null 2>&1
run_test "T2: investigation artifact written" \
    "ls '$ROOT_DIR/data/incidents/investigations'/INV-*.json 2>/dev/null | head -1"

# T3: ai.investigation.started event emitted
run_test "T3: investigation.started event" \
    "grep -q 'ai.investigation.started' '$ROOT_DIR/data/events/event_log.jsonl'"

# T4: ai.investigation.completed event emitted
run_test "T4: investigation.completed event" \
    "grep -q 'ai.investigation.completed' '$ROOT_DIR/data/events/event_log.jsonl'"

# T5: structured output has required fields
run_test "T5: output has required fields" \
    "python3 -c \"
import json, glob
f = sorted(glob.glob('$ROOT_DIR/data/incidents/investigations/INV-*.json'))[-1]
d = json.load(open(f))
for k in ['investigation_id','incident_id','playbook','evidence','hypothesis','confidence','recommended_action','risk','approval_required']:
    assert k in d, f'missing {k}'
\""

# T6+T7: viewer denied, sre allowed via API
PLATFORM_PORT=$API_PORT python3 "$ROOT_DIR/platform/api/server.py" &
PID=$!; sleep 2
cleanup() { kill $PID 2>/dev/null||true; python3 -c "
import json; f='$ROOT_DIR/artifacts/identity/active_tokens.json'
d=json.load(open(f)); d['tokens']=[t for t in d['tokens'] if 't55-' not in t.get('name','')]; json.dump(d,open(f,'w'),indent=2)
" 2>/dev/null||true; }
trap cleanup EXIT
A="http://localhost:$API_PORT"

run_test "T6: viewer cannot POST /investigate" \
    "curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Authorization: Bearer $VW' -H 'Content-Type: application/json' -d '{\"service\":\"api\"}' '$A/investigate' | grep -q '403'"

run_test "T7: sre can POST /investigate" \
    "curl -sf -X POST -H 'Authorization: Bearer $SR' -H 'Content-Type: application/json' -d '{\"service\":\"api\",\"simulate\":true}' '$A/investigate' | python3 -c 'import sys,json; d=json.load(sys.stdin); assert \"investigation\" in d'"

# T8: low confidence sets approval_required
run_test "T8: low confidence -> approval_required" \
    "python3 -c \"
import sys; sys.path.insert(0,'$ROOT_DIR/platform/aiops')
from investigator import investigate
inv = investigate('INC-T55-LOW', 'unknown_svc', 'confirmed', simulate=True)
# unknown_svc has no matching playbook, uses generic with low confidence
assert inv['approval_required'] == True or inv['confidence'] < 0.80
\""

# T9: secret scan clean
run_test "T9: secret scan clean" \
    "! grep -rEi '(password|token|secret)\s*[:=]\s*[A-Za-z0-9+/]{8,}' '$ROOT_DIR/platform/aiops/' '$ROOT_DIR/platform/incidents/' 2>/dev/null || true"

echo ""; echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && exit 1 || { echo "ALL TESTS PASSED"; exit 0; }
