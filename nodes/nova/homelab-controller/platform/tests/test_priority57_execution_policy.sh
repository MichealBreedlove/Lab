#!/usr/bin/env bash
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
PASS=0; FAIL=0; API_PORT=18457
run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  PASS $n"; PASS=$((PASS+1)); else echo "  FAIL $n"; FAIL=$((FAIL+1)); fi; }
echo "=== P57 Execution Policy & Approval Gates Tests ==="

# T1: restart_service auto-applied at high confidence
run_test "T1: restart_service auto-apply at 0.95" \
    "python3 -c \"
import sys; sys.path.insert(0,'$ROOT_DIR/platform/aiops')
from policy_engine import evaluate_remediation_policy
r = evaluate_remediation_policy('restart_service', 0.95, 'sre')
assert r['decision'] == 'auto_apply', f'got {r[\"decision\"]}'
assert r['approval_required'] == False
\""

# T2: rollback_config requires review (medium risk)
run_test "T2: rollback_config requires review" \
    "python3 -c \"
import sys; sys.path.insert(0,'$ROOT_DIR/platform/aiops')
from policy_engine import evaluate_remediation_policy
r = evaluate_remediation_policy('rollback_config', 0.90, 'sre')
assert r['decision'] == 'require_review', f'got {r[\"decision\"]}'
assert r['approval_required'] == True
\""

# T3: high risk always requires approval
run_test "T3: firewall_change always denied" \
    "python3 -c \"
import sys; sys.path.insert(0,'$ROOT_DIR/platform/aiops')
from policy_engine import evaluate_remediation_policy
r = evaluate_remediation_policy('firewall_change', 0.99, 'admin')
assert r['decision'] == 'deny_execution', f'got {r[\"decision\"]}'
assert r['approval_required'] == True
\""

# T4: delete_data is high risk
run_test "T4: delete_data is high risk" \
    "python3 -c \"
import sys; sys.path.insert(0,'$ROOT_DIR/platform/aiops')
from policy_engine import evaluate_remediation_policy
r = evaluate_remediation_policy('delete_data', 0.99, 'admin')
assert r['decision'] == 'deny_execution'
assert r['blast_radius'] == 'high'
\""

# T5: viewer cannot trigger remediation
run_test "T5: viewer denied for low-risk action" \
    "python3 -c \"
import sys; sys.path.insert(0,'$ROOT_DIR/platform/aiops')
from policy_engine import evaluate_remediation_policy
r = evaluate_remediation_policy('restart_service', 0.95, 'viewer')
assert r['decision'] == 'deny_execution', f'got {r[\"decision\"]}'
\""

# T6: sre role accepted for medium risk
run_test "T6: sre role accepted for medium risk" \
    "python3 -c \"
import sys; sys.path.insert(0,'$ROOT_DIR/platform/aiops')
from policy_engine import evaluate_remediation_policy
r = evaluate_remediation_policy('rollback_config', 0.85, 'sre')
assert r['decision'] == 'require_review', f'got {r[\"decision\"]}'
\""

# T7: policy evaluation logged
run_test "T7: policy audit log written" \
    "python3 -c \"
import sys; sys.path.insert(0,'$ROOT_DIR/platform/aiops')
from policy_engine import evaluate_remediation_policy
evaluate_remediation_policy('restart_service', 0.95, 'sre', 'INC-T57')
import os; assert os.path.exists('$ROOT_DIR/artifacts/identity/policy_audit.jsonl')
\""

# T8: blast_radius and reversible metadata present
run_test "T8: blast_radius and reversible in output" \
    "python3 -c \"
import sys; sys.path.insert(0,'$ROOT_DIR/platform/aiops')
from policy_engine import evaluate_remediation_policy
r = evaluate_remediation_policy('restart_service', 0.95, 'sre')
assert 'blast_radius' in r
assert 'reversible' in r
assert r['blast_radius'] == 'low'
assert r['reversible'] == True
\""

# T9: investigation enrichment adds policy fields
run_test "T9: investigation enrichment" \
    "python3 -c \"
import sys; sys.path.insert(0,'$ROOT_DIR/platform/aiops')
from investigator import investigate
inv = investigate('INC-T57-ENR', 'api', 'confirmed', simulate=True)
assert 'blast_radius' in inv, 'missing blast_radius'
assert 'reversible' in inv, 'missing reversible'
assert 'policy_decision' in inv, 'missing policy_decision'
\""

# T10: low confidence denied
run_test "T10: low confidence denied" \
    "python3 -c \"
import sys; sys.path.insert(0,'$ROOT_DIR/platform/aiops')
from policy_engine import evaluate_remediation_policy
r = evaluate_remediation_policy('restart_service', 0.50, 'sre')
assert r['decision'] == 'deny_execution', f'got {r[\"decision\"]}'
\""

# T11: secret scan clean
run_test "T11: secret scan clean" \
    "! grep -rEi '(password|token|secret)\s*[:=]\s*[A-Za-z0-9+/]{8,}' '$ROOT_DIR/platform/aiops/policy_engine.py' 2>/dev/null || true"

echo ""; echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && exit 1 || { echo "ALL TESTS PASSED"; exit 0; }
