#!/usr/bin/env bash
# P75 — Memory-Aware Investigation tests
set -euo pipefail
cd "$(dirname "$0")/../.."
PASS=0; FAIL=0
check() { if eval "$2"; then echo "  [PASS] $1"; ((PASS++)); else echo "  [FAIL] $1"; ((FAIL++)); fi; }

echo "=== P75: Memory-Aware Investigation ==="

# T1: investigation_context.py exists
check "investigation_context.py exists" "test -f platform/memory/investigation_context.py"

# T2: build_investigation_context is importable
check "investigation_context imports" "python3 -c 'import sys; sys.path.insert(0,\".\"); sys.path.insert(0,\"platform/memory\"); from investigation_context import build_investigation_context'"

# T3: context returns expected fields
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from investigation_context import build_investigation_context
ctx = build_investigation_context('api_down', ['api','nova'])
fields = ['related_cases','historical_success_rate','prior_recommended_actions','memory_informed_confidence']
print(all(f in ctx for f in fields))
")
check "context returns all expected fields" "[ '$RESULT' = 'True' ]"

# T4: context with prior remediations adjusts confidence
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from store import store_memory
from investigation_context import build_investigation_context
# Seed successful remediations
for i in range(5):
    store_memory('remediation', 'jasper', {'action':'rollback_config','outcome':'success'}, tags=['api_down','nova'], confidence=0.9)
ctx = build_investigation_context('api_down', ['api_down','nova'])
print(ctx['memory_informed_confidence'] >= 0.80)
")
check "successful history raises confidence" "[ '$RESULT' = 'True' ]"

# T5: prior_recommended_actions ranked by success
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from store import store_memory
from investigation_context import build_investigation_context
store_memory('remediation', 'jasper', {'action':'restart_service','outcome':'success'}, tags=['p75_rank'])
store_memory('remediation', 'jasper', {'action':'restart_service','outcome':'success'}, tags=['p75_rank'])
store_memory('remediation', 'jasper', {'action':'manual_fix','outcome':'failed'}, tags=['p75_rank'])
ctx = build_investigation_context('test', ['p75_rank'])
if ctx['prior_recommended_actions']:
    print(ctx['prior_recommended_actions'][0]['action'])
else:
    print('EMPTY')
")
check "actions ranked by success rate" "[ '$RESULT' = 'restart_service' ]"

# T6: record_investigation_to_memory stores entry
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from investigation_context import record_investigation_to_memory
from store import get_memory
entry = record_investigation_to_memory('INC-P75', 'api_down', {'summary':'test','confidence':0.8,'recommended_action':'restart'}, tags=['p75'])
got = get_memory(entry['memory_id'])
print(got['category'])
")
check "record_investigation_to_memory stores entry" "[ '$RESULT' = 'investigation' ]"

# T7: record_remediation_to_memory stores entry
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from investigation_context import record_remediation_to_memory
from store import get_memory
entry = record_remediation_to_memory('INC-P75-R', 'rollback_config', 'success', tags=['p75_rem'])
got = get_memory(entry['memory_id'])
print(got['payload']['outcome'])
")
check "record_remediation_to_memory stores outcome" "[ '$RESULT' = 'success' ]"

# T8: historical_success_rate computed correctly
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from store import store_memory
from investigation_context import build_investigation_context
store_memory('remediation', 'jasper', {'action':'fix','outcome':'success'}, tags=['p75_rate'], confidence=0.9)
store_memory('remediation', 'jasper', {'action':'fix','outcome':'failed'}, tags=['p75_rate'], confidence=0.9)
ctx = build_investigation_context('test', ['p75_rate'])
rate = ctx['historical_success_rate']
print(rate is not None and 0 <= rate <= 1)
")
check "historical_success_rate in [0,1]" "[ '$RESULT' = 'True' ]"

# T9: context works with no history (cold start)
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from investigation_context import build_investigation_context
ctx = build_investigation_context('totally_new_incident_type', ['never_seen_tag_xyz'])
print(ctx['historical_success_rate'] is None and ctx['memory_informed_confidence'] > 0)
")
check "cold start returns safe defaults" "[ '$RESULT' = 'True' ]"

# T10: investigator.py still imports and has memory enrichment
check "investigator.py has memory enrichment" "grep -q 'build_investigation_context' platform/aiops/investigator.py"

echo ""
echo "P75 Results: $PASS passed, $FAIL failed ($(($PASS+$FAIL)) total)"
exit $FAIL
