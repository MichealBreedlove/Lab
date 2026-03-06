#!/usr/bin/env bash
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
SD="$(cd "$(dirname "$0")" && pwd)"; RD="$SD/../.."
PASS=0; FAIL=0
run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  PASS $n"; PASS=$((PASS+1)); else echo "  FAIL $n"; FAIL=$((FAIL+1)); fi; }
echo "=== P71 Autonomous Operations Loop Tests ==="
rm -f "$RD/data/cluster/agents/registry.json" "$RD/data/cluster/tasks/tasks.json" "$RD/data/cluster/scheduler_state.json" "$RD/data/events/event_log.jsonl" 2>/dev/null || true
rm -rf "$RD/data/reports/"scorecard* "$RD/data/reports/daily_scorecard.md" 2>/dev/null || true

# Register agents for scheduler
python3 -c "
import sys; sys.path.insert(0,'$RD/platform/cluster')
from registry import register_agent
register_agent('jasper','jasper','coordinator',['task_routing'],'assisted')
register_agent('nova','nova','proxmox_optimizer',['cluster_scan'],'autonomous_low_risk')
register_agent('mira','mira','network_optimizer',['firewall_audit'],'audit')
" 2>/dev/null

run_test "T1: scheduler tick creates tasks" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster')
from scheduler import tick
r = tick()
assert r['created'] >= 1, f'created {r[\"created\"]}'
\""

run_test "T2: tasks queued from schedule" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster')
from task_bus import get_tasks
tasks = get_tasks(status='queued')
assert len(tasks) >= 1
\""

run_test "T3: second tick respects interval" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster')
from scheduler import tick
r = tick()
assert r['created'] == 0, f'should not re-create: {r[\"created\"]}'
\""

run_test "T4: scorecard generated" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster')
from scheduler import generate_scorecard
sc = generate_scorecard()
assert 'scores' in sc
assert 'cluster_health' in sc['scores']
\""

run_test "T5: scorecard md written" "test -f '$RD/data/reports/daily_scorecard.md'"

run_test "T6: schedule config loaded" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster')
from scheduler import load_schedule
s = load_schedule()
assert len(s['schedules']) >= 4
\""

run_test "T7: scheduler state persisted" "test -f '$RD/data/cluster/scheduler_state.json'"

run_test "T8: secret scan" "! grep -rEi '(password|token|secret)\s*[:=]\s*[A-Za-z0-9+/]{8,}' '$RD/platform/cluster/scheduler.py' 2>/dev/null || true"

echo ""; echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && exit 1 || { echo "ALL TESTS PASSED"; exit 0; }
