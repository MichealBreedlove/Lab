#!/usr/bin/env bash
set -uo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
SD="$(cd "$(dirname "$0")" && pwd)"; RD="$SD/../.."
PASS=0; FAIL=0
run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  PASS $n"; PASS=$((PASS+1)); else echo "  FAIL $n"; FAIL=$((FAIL+1)); fi; }
echo "=== P70 Artifact Handoff Tests ==="
rm -rf "$RD/data/cluster/artifacts/"HO-* "$RD/data/events/event_log.jsonl" 2>/dev/null || true

run_test "T1: create handoff" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster')
from handoff import create_handoff
h = create_handoff('mira','jasper','network_audit_report',{'findings':3})
assert h['source_agent'] == 'mira'
assert h['target_agent'] == 'jasper'
assert h['consumed'] == False
\""

run_test "T2: handoff file written" "ls '$RD/data/cluster/artifacts'/HO-*.json 2>/dev/null | head -1"

run_test "T3: pending handoffs" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster')
from handoff import get_pending_handoffs
h = get_pending_handoffs('jasper')
assert len(h) >= 1
\""

run_test "T4: consume handoff" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster')
from handoff import get_pending_handoffs, consume_handoff
h = get_pending_handoffs('jasper')
result = consume_handoff(h[0]['handoff_id'], 'jasper')
assert result['consumed'] == True
\""

run_test "T5: wrong agent cannot consume" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster')
from handoff import create_handoff, consume_handoff
h = create_handoff('nova','jasper','report',{})
result = consume_handoff(h['handoff_id'], 'mira')
assert result is None
\""

run_test "T6: workflow composition" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster')
from handoff import compose_workflow
wf = compose_workflow([
    {'agent':'mira','task_type':'audit_firewall'},
    {'agent':'jasper','task_type':'generate_artifact','depends_on':1},
])
assert len(wf['steps']) == 2
assert wf['steps'][1]['depends_on'] == 1
\""

run_test "T7: handoff event emitted" "grep -q 'cluster.artifact.handoff' '$RD/data/events/event_log.jsonl'"

echo ""; echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && exit 1 || { echo "ALL TESTS PASSED"; exit 0; }
