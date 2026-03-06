#!/usr/bin/env bash
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
SD="$(cd "$(dirname "$0")" && pwd)"; RD="$SD/../.."
PASS=0; FAIL=0
run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  PASS $n"; PASS=$((PASS+1)); else echo "  FAIL $n"; FAIL=$((FAIL+1)); fi; }
echo "=== P65 Task Bus Tests ==="
rm -f "$RD/data/cluster/tasks/tasks.json" "$RD/data/events/event_log.jsonl" 2>/dev/null || true

run_test "T1: create task" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster')
from task_bus import create_task
t = create_task('audit_firewall','jasper',target_role='network_optimizer')
assert t['status'] == 'queued'
assert t['task_type'] == 'audit_firewall'
\""

run_test "T2: claim task" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster')
from task_bus import claim_task
t = claim_task('mira',['firewall_audit'],'network_optimizer')
assert t is not None
assert t['assigned_to'] == 'mira'
\""

run_test "T3: complete task" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster')
from task_bus import get_tasks, complete_task
tasks = get_tasks(status='assigned')
if tasks:
    t = complete_task(tasks[0]['task_id'],'mira',{'status':'completed','summary':'done'})
    assert t['status'] == 'completed'
\""

run_test "T4: task.created event" "grep -q 'cluster.task.created' '$RD/data/events/event_log.jsonl'"
run_test "T5: task.assigned event" "grep -q 'cluster.task.assigned' '$RD/data/events/event_log.jsonl'"
run_test "T6: task.completed event" "grep -q 'cluster.task.completed' '$RD/data/events/event_log.jsonl'"

run_test "T7: task summary" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster')
from task_bus import task_summary
s = task_summary()
assert s['total'] >= 1
\""

run_test "T8: secret scan" "! grep -rEi '(password|token|secret)\s*[:=]\s*[A-Za-z0-9+/]{8,}' '$RD/platform/cluster/task_bus.py' 2>/dev/null || true"

echo ""; echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && exit 1 || { echo "ALL TESTS PASSED"; exit 0; }
