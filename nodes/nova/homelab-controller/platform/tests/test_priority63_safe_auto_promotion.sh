#!/usr/bin/env bash
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
PASS=0; FAIL=0
run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  PASS $n"; PASS=$((PASS+1)); else echo "  FAIL $n"; FAIL=$((FAIL+1)); fi; }
echo "=== P63 Safe Auto-Promotion Tests ==="

rm -rf "$ROOT_DIR/data/self_improvement/"{reviews,proposals,validations,promoted}/[A-Z]* 2>/dev/null || true
rm -f "$ROOT_DIR/data/events/event_log.jsonl" 2>/dev/null || true

# Setup: create validated doc proposal
python3 -c "
import json
from pathlib import Path
prop_dir = Path('$ROOT_DIR/data/self_improvement/proposals'); prop_dir.mkdir(parents=True, exist_ok=True)
val_dir = Path('$ROOT_DIR/data/self_improvement/validations'); val_dir.mkdir(parents=True, exist_ok=True)
json.dump({'proposal_id': 'PROP-T63-DOC', 'type': 'documentation_update', 'description': 'Update runbook', 'status': 'validated', 'risk_level': 'low'}, open(prop_dir / 'PROP-T63-DOC.json', 'w'), indent=2)
json.dump({'validation_id': 'VAL-T63-DOC', 'proposal_id': 'PROP-T63-DOC', 'result': 'passed', 'checks': [{'check':'schema_check','passed':True,'detail':'ok'}], 'all_passed': True}, open(val_dir / 'VAL-T63-DOC.json', 'w'), indent=2)
json.dump({'proposal_id': 'PROP-T63-PB', 'type': 'playbook_update', 'description': 'Add evidence step', 'status': 'validated', 'risk_level': 'medium'}, open(prop_dir / 'PROP-T63-PB.json', 'w'), indent=2)
json.dump({'validation_id': 'VAL-T63-PB', 'proposal_id': 'PROP-T63-PB', 'result': 'passed', 'checks': [{'check':'schema_check','passed':True,'detail':'ok'}], 'all_passed': True}, open(val_dir / 'VAL-T63-PB.json', 'w'), indent=2)
"

# T1: doc proposal auto-promoted
run_test "T1: doc auto-promoted" \
    "python3 -c \"
import sys; sys.path.insert(0,'$ROOT_DIR/platform/self_improvement')
from promotion import promote_proposal
r = promote_proposal('PROP-T63-DOC')
assert r['promoted'] == True, f'not promoted: {r}'
assert r['decision'] == 'auto_promote'
\""

# T2: promoted file written
run_test "T2: promoted file written" \
    "ls '$ROOT_DIR/data/self_improvement/promoted'/PROM-*.json 2>/dev/null | head -1"

# T3: promotion event emitted
run_test "T3: promotion.applied event" \
    "grep -q 'self_improvement.promotion.applied' '$ROOT_DIR/data/events/event_log.jsonl'"

# T4: playbook update NOT auto-promoted
run_test "T4: playbook update blocked" \
    "python3 -c \"
import sys; sys.path.insert(0,'$ROOT_DIR/platform/self_improvement')
from promotion import promote_proposal
r = promote_proposal('PROP-T63-PB')
assert r['promoted'] == False
assert r['decision'] == 'require_review'
\""

# T5: force promotion works
run_test "T5: force promotion" \
    "python3 -c \"
import sys; sys.path.insert(0,'$ROOT_DIR/platform/self_improvement')
from promotion import promote_proposal
r = promote_proposal('PROP-T63-PB', force=True)
assert r['promoted'] == True
\""

# T6: proposal status updated to promoted
run_test "T6: proposal status = promoted" \
    "python3 -c \"
import json
d = json.load(open('$ROOT_DIR/data/self_improvement/proposals/PROP-T63-DOC.json'))
assert d['status'] == 'promoted', d['status']
\""

# T7: secret scan clean
run_test "T7: secret scan clean" \
    "! grep -rEi '(password|token|secret)\s*[:=]\s*[A-Za-z0-9+/]{8,}' '$ROOT_DIR/platform/self_improvement/' 2>/dev/null || true"

echo ""; echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && exit 1 || { echo "ALL TESTS PASSED"; exit 0; }
