#!/usr/bin/env bash
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
PASS=0; FAIL=0
run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  PASS $n"; PASS=$((PASS+1)); else echo "  FAIL $n"; FAIL=$((FAIL+1)); fi; }
echo "=== P61 Validation Runner Tests ==="

rm -rf "$ROOT_DIR/data/self_improvement/"{reviews,proposals,validations}/[A-Z]* 2>/dev/null || true
rm -f "$ROOT_DIR/data/events/event_log.jsonl" 2>/dev/null || true

# Create review + proposal chain
PROP_ID=$(python3 -c "
import sys; sys.path.insert(0,'$ROOT_DIR/platform/self_improvement')
from reviewer import generate_review
from proposer import generate_proposals_from_review
r = generate_review('INC-T61', 'restart_service', 'resolved')
props = generate_proposals_from_review(r['review_id'])
if props: print(props[0]['proposal_id'])
else: print('NONE')
" 2>/dev/null | tail -1)

# T1: validation runs
run_test "T1: validation runs" \
    "python3 '$ROOT_DIR/platform/self_improvement/validator.py' validate $PROP_ID 2>&1 | grep -q 'OK'"

# T2: validation file written
run_test "T2: validation file written" \
    "ls '$ROOT_DIR/data/self_improvement/validations'/VAL-*.json 2>/dev/null | head -1"

# T3: schema_check present
run_test "T3: schema_check in results" \
    "python3 -c \"
import json, glob
f = sorted(glob.glob('$ROOT_DIR/data/self_improvement/validations/VAL-*.json'))[-1]
d = json.load(open(f))
checks = [c['check'] for c in d['checks']]
assert 'schema_check' in checks
\""

# T4: simulation_check present
run_test "T4: simulation_check in results" \
    "python3 -c \"
import json, glob
f = sorted(glob.glob('$ROOT_DIR/data/self_improvement/validations/VAL-*.json'))[-1]
d = json.load(open(f))
checks = [c['check'] for c in d['checks']]
assert 'simulation_check' in checks
\""

# T5: test_suite_check present
run_test "T5: test_suite_check in results" \
    "python3 -c \"
import json, glob
f = sorted(glob.glob('$ROOT_DIR/data/self_improvement/validations/VAL-*.json'))[-1]
d = json.load(open(f))
checks = [c['check'] for c in d['checks']]
assert 'test_suite_check' in checks
\""

# T6: validation event emitted
run_test "T6: validation.completed event" \
    "grep -q 'self_improvement.validation.completed' '$ROOT_DIR/data/events/event_log.jsonl'"

# T7: proposal status updated
run_test "T7: proposal status updated" \
    "python3 -c \"
import json
d = json.load(open('$ROOT_DIR/data/self_improvement/proposals/$PROP_ID.json'))
assert d['status'] in ('validated','validation_failed'), d['status']
\""

echo ""; echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && exit 1 || { echo "ALL TESTS PASSED"; exit 0; }
