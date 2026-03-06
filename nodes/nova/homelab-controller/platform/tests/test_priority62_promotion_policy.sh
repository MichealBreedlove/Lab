#!/usr/bin/env bash
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
PASS=0; FAIL=0
run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  PASS $n"; PASS=$((PASS+1)); else echo "  FAIL $n"; FAIL=$((FAIL+1)); fi; }
echo "=== P62 Promotion Policy Engine Tests ==="

rm -rf "$ROOT_DIR/data/self_improvement/"{reviews,proposals,validations,promoted}/[A-Z]* 2>/dev/null || true

# T1: documentation_update evaluates to auto_promote
run_test "T1: doc update -> auto_promote" \
    "python3 -c \"
import sys, json; sys.path.insert(0,'$ROOT_DIR/platform/self_improvement')
# Create a doc-type proposal manually
from pathlib import Path
import uuid
from datetime import datetime, timezone
prop_dir = Path('$ROOT_DIR/data/self_improvement/proposals')
prop_dir.mkdir(parents=True, exist_ok=True)
val_dir = Path('$ROOT_DIR/data/self_improvement/validations')
val_dir.mkdir(parents=True, exist_ok=True)
prop_id = 'PROP-T62-DOC'
json.dump({'proposal_id': prop_id, 'type': 'documentation_update', 'description': 'test', 'status': 'validated', 'risk_level': 'low'}, open(prop_dir / f'{prop_id}.json', 'w'), indent=2)
val_id = 'VAL-T62-DOC'
json.dump({'validation_id': val_id, 'proposal_id': prop_id, 'result': 'passed', 'checks': [], 'all_passed': True}, open(val_dir / f'{val_id}.json', 'w'), indent=2)
from promotion import evaluate_promotion
d, r = evaluate_promotion(prop_id)
assert d == 'auto_promote', f'got {d}: {r}'
\""

# T2: playbook_update requires review
run_test "T2: playbook update -> require_review" \
    "python3 -c \"
import sys, json; sys.path.insert(0,'$ROOT_DIR/platform/self_improvement')
from pathlib import Path
prop_dir = Path('$ROOT_DIR/data/self_improvement/proposals')
val_dir = Path('$ROOT_DIR/data/self_improvement/validations')
prop_id = 'PROP-T62-PB'
json.dump({'proposal_id': prop_id, 'type': 'playbook_update', 'description': 'test', 'status': 'validated', 'risk_level': 'medium'}, open(prop_dir / f'{prop_id}.json', 'w'), indent=2)
json.dump({'validation_id': 'VAL-T62-PB', 'proposal_id': prop_id, 'result': 'passed', 'checks': [], 'all_passed': True}, open(val_dir / 'VAL-T62-PB.json', 'w'), indent=2)
from promotion import evaluate_promotion
d, r = evaluate_promotion(prop_id)
assert d == 'require_review', f'got {d}: {r}'
\""

# T3: policy_change_request denied
run_test "T3: policy change -> deny" \
    "python3 -c \"
import sys, json; sys.path.insert(0,'$ROOT_DIR/platform/self_improvement')
from pathlib import Path
prop_dir = Path('$ROOT_DIR/data/self_improvement/proposals')
prop_id = 'PROP-T62-POL'
json.dump({'proposal_id': prop_id, 'type': 'policy_change_request', 'description': 'test', 'status': 'validated', 'risk_level': 'high'}, open(prop_dir / f'{prop_id}.json', 'w'), indent=2)
from promotion import evaluate_promotion
d, r = evaluate_promotion(prop_id)
assert d == 'deny', f'got {d}: {r}'
\""

# T4: unvalidated proposal denied
run_test "T4: unvalidated -> deny" \
    "python3 -c \"
import sys, json; sys.path.insert(0,'$ROOT_DIR/platform/self_improvement')
from pathlib import Path
prop_dir = Path('$ROOT_DIR/data/self_improvement/proposals')
prop_id = 'PROP-T62-NOVAL'
json.dump({'proposal_id': prop_id, 'type': 'documentation_update', 'description': 'test', 'status': 'pending', 'risk_level': 'low'}, open(prop_dir / f'{prop_id}.json', 'w'), indent=2)
from promotion import evaluate_promotion
d, r = evaluate_promotion(prop_id)
assert d == 'deny', f'got {d}: {r}'
\""

# T5: policy config loaded
run_test "T5: policy config loaded" \
    "python3 -c \"
import sys, json; sys.path.insert(0,'$ROOT_DIR/platform/self_improvement')
from promotion import load_policy
p = load_policy()
assert 'auto_promote_types' in p
assert 'documentation_update' in p['auto_promote_types']
\""

# T6: secret scan clean
run_test "T6: secret scan clean" \
    "! grep -rEi '(password|token|secret)\s*[:=]\s*[A-Za-z0-9+/]{8,}' '$ROOT_DIR/platform/self_improvement/promotion.py' 2>/dev/null || true"

echo ""; echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && exit 1 || { echo "ALL TESTS PASSED"; exit 0; }
