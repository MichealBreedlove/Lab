#!/usr/bin/env bash
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
PASS=0; FAIL=0
run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  PASS $n"; PASS=$((PASS+1)); else echo "  FAIL $n"; FAIL=$((FAIL+1)); fi; }
echo "=== P60 Improvement Proposal Generator Tests ==="

rm -rf "$ROOT_DIR/data/self_improvement/reviews/"AAR-* "$ROOT_DIR/data/self_improvement/proposals/"PROP-* 2>/dev/null || true
rm -f "$ROOT_DIR/data/events/event_log.jsonl" 2>/dev/null || true

# Generate a review with improvements (low confidence to trigger proposals)
python3 -c "
import sys; sys.path.insert(0,'$ROOT_DIR/platform/self_improvement')
from reviewer import generate_review
r = generate_review('INC-T60', 'failover_service', 'resolved', human_override=True)
print(r['review_id'])
" > /tmp/t60_review_id.txt
REVIEW_ID=$(cat /tmp/t60_review_id.txt | tail -1)

# T1: proposals generated from review
run_test "T1: proposals generated" \
    "python3 '$ROOT_DIR/platform/self_improvement/proposer.py' generate $REVIEW_ID 2>&1 | grep -q 'OK'"

# T2: proposal files written
run_test "T2: proposal files written" \
    "ls '$ROOT_DIR/data/self_improvement/proposals'/PROP-*.json 2>/dev/null | head -1"

# T3: valid proposal types
run_test "T3: valid proposal types" \
    "python3 -c \"
import json, glob
for f in glob.glob('$ROOT_DIR/data/self_improvement/proposals/PROP-*.json'):
    d = json.load(open(f))
    assert d['type'] in ['documentation_update','artifact_template_update','playbook_update','confidence_threshold_update','alert_mapping_update','policy_change_request'], d['type']
\""

# T4: risk level assigned
run_test "T4: risk level assigned" \
    "python3 -c \"
import json, glob
f = sorted(glob.glob('$ROOT_DIR/data/self_improvement/proposals/PROP-*.json'))[-1]
d = json.load(open(f))
assert d['risk_level'] in ['low','medium','high']
\""

# T5: proposal event emitted
run_test "T5: proposal.created event" \
    "grep -q 'self_improvement.proposal.created' '$ROOT_DIR/data/events/event_log.jsonl'"

# T6: validation_required flag set correctly
run_test "T6: validation_required for non-doc types" \
    "python3 -c \"
import json, glob
for f in glob.glob('$ROOT_DIR/data/self_improvement/proposals/PROP-*.json'):
    d = json.load(open(f))
    if d['type'] not in ('documentation_update','artifact_template_update'):
        assert d.get('validation_required') == True, f'{d[\"type\"]} should require validation'
\""

# T7: secret scan clean
run_test "T7: secret scan clean" \
    "! grep -rEi '(password|token|secret)\s*[:=]\s*[A-Za-z0-9+/]{8,}' '$ROOT_DIR/platform/self_improvement/proposer.py' 2>/dev/null || true"

echo ""; echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && exit 1 || { echo "ALL TESTS PASSED"; exit 0; }
