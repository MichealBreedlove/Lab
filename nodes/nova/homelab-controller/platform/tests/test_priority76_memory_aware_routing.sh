#!/usr/bin/env bash
# P76 — Memory-Aware Routing tests
set -euo pipefail
cd "$(dirname "$0")/../.."
PASS=0; FAIL=0
check() { if eval "$2"; then echo "  [PASS] $1"; ((PASS++)); else echo "  [FAIL] $1"; ((FAIL++)); fi; }

echo "=== P76: Memory-Aware Routing ==="

# T1: routing_history.py exists
check "routing_history.py exists" "test -f platform/memory/routing_history.py"

# T2: routing_history.py is importable
check "routing_history imports" "python3 -c 'import sys; sys.path.insert(0,\".\"); sys.path.insert(0,\"platform/memory\"); from routing_history import record_routing_outcome, get_agent_performance'"

# T3: record_routing_outcome stores entry
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from routing_history import record_routing_outcome
from store import get_memory
entry = record_routing_outcome('TASK-P76-01', 'audit_firewall', 'mira', 'success', duration_seconds=12.5)
got = get_memory(entry['memory_id'])
print(got['payload']['outcome'])
")
check "record_routing_outcome stores entry" "[ '$RESULT' = 'success' ]"

# T4: get_agent_performance returns metrics
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from routing_history import record_routing_outcome, get_agent_performance
record_routing_outcome('TASK-P76-02', 'audit_firewall', 'mira', 'success', duration_seconds=10)
record_routing_outcome('TASK-P76-03', 'audit_firewall', 'mira', 'success', duration_seconds=15)
record_routing_outcome('TASK-P76-04', 'audit_firewall', 'mira', 'failed', duration_seconds=5)
perf = get_agent_performance('mira', task_type='audit_firewall')
print(perf['total_tasks'] >= 3 and perf['success_rate'] is not None)
")
check "get_agent_performance returns metrics" "[ '$RESULT' = 'True' ]"

# T5: success_rate computed correctly
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from routing_history import record_routing_outcome, get_agent_performance
for i in range(4):
    record_routing_outcome(f'TASK-P76-S{i}', 'p76_test', 'nova', 'success')
record_routing_outcome('TASK-P76-SF', 'p76_test', 'nova', 'failed')
perf = get_agent_performance('nova', task_type='p76_test')
print(perf['success_rate'] >= 0.7)
")
check "success_rate >= 0.7 for 4/5 success" "[ '$RESULT' = 'True' ]"

# T6: get_best_agent_for_task ranks agents
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from routing_history import record_routing_outcome, get_best_agent_for_task
for i in range(3):
    record_routing_outcome(f'TASK-P76-R{i}', 'rank_test', 'mira', 'success')
record_routing_outcome('TASK-P76-R9', 'rank_test', 'orin', 'failed')
rankings = get_best_agent_for_task('rank_test', ['mira','orin'], min_history=1)
print(rankings[0][0])
")
check "best agent ranked first" "[ '$RESULT' = 'mira' ]"

# T7: average_completion_time tracked
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from routing_history import record_routing_outcome, get_agent_performance
record_routing_outcome('TASK-P76-T1', 'time_test', 'orin', 'success', duration_seconds=20)
record_routing_outcome('TASK-P76-T2', 'time_test', 'orin', 'success', duration_seconds=30)
perf = get_agent_performance('orin', task_type='time_test')
print(perf['average_completion_time'] is not None and perf['average_completion_time'] > 0)
")
check "average_completion_time tracked" "[ '$RESULT' = 'True' ]"

# T8: router.py has memory-aware routing code
check "router.py has memory routing" "grep -q 'routing_history' platform/cluster/router.py"

# T9: get_all_agent_performance_summary works
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from routing_history import get_all_agent_performance_summary
s = get_all_agent_performance_summary()
print(type(s) is dict)
")
check "performance summary returns dict" "[ '$RESULT' = 'True' ]"

# T10: review_required_rate tracked
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from routing_history import record_routing_outcome, get_agent_performance
record_routing_outcome('TASK-P76-RR1', 'review_test', 'jasper', 'success', required_review=True)
record_routing_outcome('TASK-P76-RR2', 'review_test', 'jasper', 'success', required_review=False)
perf = get_agent_performance('jasper', task_type='review_test')
print(perf['review_required_rate'] is not None)
")
check "review_required_rate tracked" "[ '$RESULT' = 'True' ]"

echo ""
echo "P76 Results: $PASS passed, $FAIL failed ($(($PASS+$FAIL)) total)"
exit $FAIL
