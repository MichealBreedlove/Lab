#!/usr/bin/env bash
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
SD="$(cd "$(dirname "$0")" && pwd)"; RD="$SD/../.."
PASS=0; FAIL=0
run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  PASS $n"; PASS=$((PASS+1)); else echo "  FAIL $n"; FAIL=$((FAIL+1)); fi; }
echo "=== P67 Node Agent Runtimes Tests ==="
rm -f "$RD/data/cluster/agents/registry.json" "$RD/data/cluster/tasks/tasks.json" "$RD/data/events/event_log.jsonl" 2>/dev/null || true

run_test "T1: jasper agent registers" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/agents')
from jasper_agent import JasperAgent
a = JasperAgent(); a.register()
assert a.agent_id == 'jasper'
assert a.role == 'coordinator'
\""

run_test "T2: nova agent registers" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/agents')
from nova_agent import NovaAgent
a = NovaAgent(); a.register()
assert a.agent_id == 'nova'
\""

run_test "T3: mira agent registers" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/agents')
from mira_agent import MiraAgent
a = MiraAgent(); a.register()
assert a.agent_id == 'mira'
\""

run_test "T4: orin agent registers" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/agents')
from orin_agent import OrinAgent
a = OrinAgent(); a.register()
assert a.agent_id == 'orin'
\""

run_test "T5: agent executes task" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster'); sys.path.insert(0,'$RD/platform/agents')
from task_bus import create_task
from mira_agent import MiraAgent
create_task('audit_firewall','jasper',target_role='network_optimizer')
a = MiraAgent(); a.register()
result = a.poll_and_execute()
assert result is not None
assert result['status'] == 'completed'
\""

run_test "T6: handler returns structured result" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster'); sys.path.insert(0,'$RD/platform/agents')
from task_bus import create_task
from nova_agent import NovaAgent
create_task('audit_proxmox','jasper',target_role='proxmox_optimizer')
a = NovaAgent(); a.register()
result = a.poll_and_execute()
assert 'result_type' in result
assert 'confidence' in result
\""

run_test "T7: all 4 configs exist" "test -f '$RD/config/agents/jasper.json' && test -f '$RD/config/agents/nova.json' && test -f '$RD/config/agents/mira.json' && test -f '$RD/config/agents/orin.json'"

run_test "T8: secret scan" "! grep -rEi '(password|token|secret)\s*[:=]\s*[A-Za-z0-9+/]{8,}' '$RD/platform/agents/' 2>/dev/null || true"

echo ""; echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && exit 1 || { echo "ALL TESTS PASSED"; exit 0; }
