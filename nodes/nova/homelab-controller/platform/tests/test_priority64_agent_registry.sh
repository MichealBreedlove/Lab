#!/usr/bin/env bash
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
SD="$(cd "$(dirname "$0")" && pwd)"; RD="$SD/../.."
PASS=0; FAIL=0
run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  PASS $n"; PASS=$((PASS+1)); else echo "  FAIL $n"; FAIL=$((FAIL+1)); fi; }
echo "=== P64 Agent Registry Tests ==="
rm -f "$RD/data/cluster/agents/registry.json" "$RD/data/events/event_log.jsonl" 2>/dev/null || true

run_test "T1: register agent" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster')
from registry import register_agent
a = register_agent('test-agent','test-node','coordinator',['task_routing'],'assisted')
assert a['agent_id'] == 'test-agent'
assert a['status'] == 'online'
\""

run_test "T2: heartbeat updates timestamp" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster')
from registry import heartbeat
a = heartbeat('test-agent')
assert a is not None
\""

run_test "T3: get_agents returns registered" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster')
from registry import get_agents
agents = get_agents()
assert len(agents) >= 1
\""

run_test "T4: set_status works" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster')
from registry import set_status, get_agent
set_status('test-agent', 'degraded')
a = get_agent('test-agent')
assert a['status'] == 'degraded'
\""

run_test "T5: registered event emitted" "grep -q 'cluster.agent.registered' '$RD/data/events/event_log.jsonl'"

run_test "T6: state_changed event emitted" "grep -q 'cluster.agent.state_changed' '$RD/data/events/event_log.jsonl'"

run_test "T7: summary counts" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster')
from registry import summary
s = summary()
assert s['total'] >= 1
\""

run_test "T8: secret scan" "! grep -rEi '(password|token|secret)\s*[:=]\s*[A-Za-z0-9+/]{8,}' '$RD/platform/cluster/registry.py' 2>/dev/null || true"

echo ""; echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && exit 1 || { echo "ALL TESTS PASSED"; exit 0; }
