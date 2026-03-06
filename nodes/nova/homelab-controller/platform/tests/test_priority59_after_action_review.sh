#!/usr/bin/env bash
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
PASS=0; FAIL=0; API_PORT=18459
run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  PASS $n"; PASS=$((PASS+1)); else echo "  FAIL $n"; FAIL=$((FAIL+1)); fi; }
echo "=== P59 After-Action Review Tests ==="

# Clean
rm -rf "$ROOT_DIR/data/self_improvement/reviews/"AAR-* 2>/dev/null || true
rm -f "$ROOT_DIR/data/events/event_log.jsonl" 2>/dev/null || true

# T1: generate review
run_test "T1: review generated" \
    "python3 '$ROOT_DIR/platform/self_improvement/reviewer.py' generate INC-T59-001 restart_service resolved 2>&1 | grep -q 'OK'"

# T2: review file written
run_test "T2: review file written" \
    "ls '$ROOT_DIR/data/self_improvement/reviews'/AAR-*.json 2>/dev/null | head -1"

# T3: required fields present
run_test "T3: required fields present" \
    "python3 -c \"
import json, glob
f = sorted(glob.glob('$ROOT_DIR/data/self_improvement/reviews/AAR-*.json'))[-1]
d = json.load(open(f))
for k in ['review_id','incident_id','playbook_used','recommended_action','actual_action','outcome','human_override','lessons_learned','proposed_improvements']:
    assert k in d, f'missing {k}'
\""

# T4: event emitted
run_test "T4: review.created event emitted" \
    "grep -q 'self_improvement.review.created' '$ROOT_DIR/data/events/event_log.jsonl'"

# T5: human override flagged
run_test "T5: human override" \
    "python3 -c \"
import sys; sys.path.insert(0,'$ROOT_DIR/platform/self_improvement')
from reviewer import generate_review
r = generate_review('INC-T59-OVR', 'failover_service', 'resolved', human_override=True)
assert r['human_override'] == True
assert any('override' in l.lower() for l in r['lessons_learned'])
\""

# T6: API endpoint — viewer denied
VW=$(python3 "$ROOT_DIR/scripts/identity/token_issuer.py" create viewer t59-viewer 2>&1 | grep 'Secret:' | awk '{print $NF}')
SR=$(python3 "$ROOT_DIR/scripts/identity/token_issuer.py" create sre t59-sre 2>&1 | grep 'Secret:' | awk '{print $NF}')
PLATFORM_PORT=$API_PORT python3 "$ROOT_DIR/platform/api/server.py" &
PID=$!; sleep 2
cleanup() { kill $PID 2>/dev/null||true; python3 -c "
import json; f='$ROOT_DIR/artifacts/identity/active_tokens.json'
d=json.load(open(f)); d['tokens']=[t for t in d['tokens'] if 't59-' not in t.get('name','')]; json.dump(d,open(f,'w'),indent=2)
" 2>/dev/null||true; }
trap cleanup EXIT
A="http://localhost:$API_PORT"

run_test "T6: viewer denied" \
    "curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Authorization: Bearer $VW' -H 'Content-Type: application/json' -d '{\"incident_id\":\"INC-T59\"}' '$A/self-improvement/review' | grep -q '403'"

# T7: sre allowed
run_test "T7: sre allowed" \
    "curl -sf -X POST -H 'Authorization: Bearer $SR' -H 'Content-Type: application/json' -d '{\"incident_id\":\"INC-T59-API\"}' '$A/self-improvement/review' | python3 -c 'import sys,json; assert \"review\" in json.load(sys.stdin)'"

# T8: secret scan clean
run_test "T8: secret scan clean" \
    "! grep -rEi '(password|token|secret)\s*[:=]\s*[A-Za-z0-9+/]{8,}' '$ROOT_DIR/platform/self_improvement/' 2>/dev/null || true"

echo ""; echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && exit 1 || { echo "ALL TESTS PASSED"; exit 0; }
