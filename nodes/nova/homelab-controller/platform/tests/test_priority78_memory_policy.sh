#!/usr/bin/env bash
# P78 — Memory Retention, Hygiene, and Policy tests
set -uo pipefail
cd "$(dirname "$0")/../.."
PASS=0; FAIL=0
check() { if eval "$2" 2>/dev/null; then echo "  [PASS] $1"; PASS=$((PASS+1)); else echo "  [FAIL] $1"; FAIL=$((FAIL+1)); fi; return 0; }

echo "=== P78: Memory Retention and Policy ==="

# T1: lifecycle.py exists
check "lifecycle.py exists" "test -f platform/memory/lifecycle.py"

# T2: memory_policy.json exists
check "memory_policy.json exists" "test -f config/memory_policy.json"

# T3: policy file has required fields
RESULT=$(python3 -c "
import json
with open('config/memory_policy.json') as f:
    p = json.load(f)
fields = ['enabled','archive_after_days','never_auto_delete','summary_rollups']
print(all(f in p for f in fields))
")
check "policy has required fields" "[ '$RESULT' = 'True' ]"

# T4: lifecycle.py is importable
check "lifecycle imports" "python3 -c 'import sys; sys.path.insert(0,\".\"); sys.path.insert(0,\"platform/memory\"); from lifecycle import archive_stale_entries, memory_hygiene_report, lifecycle_tick'"

# T5: archive_stale_entries dry-run works
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from lifecycle import archive_stale_entries
result = archive_stale_entries(dry_run=True)
print('archived' in result and 'skipped' in result)
")
check "archive dry-run returns counts" "[ '$RESULT' = 'True' ]"

# T6: memory_hygiene_report returns valid data
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from lifecycle import memory_hygiene_report
r = memory_hygiene_report()
fields = ['total_entries','active','archived','stale_candidates','by_category','policy_enabled']
print(all(f in r for f in fields))
")
check "hygiene report has all fields" "[ '$RESULT' = 'True' ]"

# T7: never_auto_delete categories protected
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from lifecycle import load_policy
p = load_policy()
protected = p.get('never_auto_delete', [])
print('policy_decision' in protected and 'operator_feedback' in protected)
")
check "policy_decision and operator_feedback protected" "[ '$RESULT' = 'True' ]"

# T8: lifecycle_tick runs without error
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from lifecycle import lifecycle_tick
result = lifecycle_tick(dry_run=True)
print('archive' in result and 'rollups' in result and 'hygiene' in result)
")
check "lifecycle_tick returns complete result" "[ '$RESULT' = 'True' ]"

# T9: generate_rollup_summary handles small datasets
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from lifecycle import generate_rollup_summary
result = generate_rollup_summary('routing_history', min_entries=9999)
print(result['status'] == 'skipped')
")
check "rollup skips when too few entries" "[ '$RESULT' = 'True' ]"

# T10: archive_after_days configured for all categories
RESULT=$(python3 -c "
import json
with open('config/memory_policy.json') as f:
    p = json.load(f)
categories = ['routing_history','optimization','incident','investigation','remediation',
              'infrastructure','operator_feedback','policy_decision','self_improvement']
days = p['archive_after_days']
print(all(c in days for c in categories))
")
check "all categories have retention days" "[ '$RESULT' = 'True' ]"

echo ""
echo "P78 Results: $PASS passed, $FAIL failed ($(($PASS+$FAIL)) total)"
exit $FAIL
