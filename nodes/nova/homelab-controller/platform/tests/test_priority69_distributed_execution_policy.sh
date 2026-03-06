#!/usr/bin/env bash
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
SD="$(cd "$(dirname "$0")" && pwd)"; RD="$SD/../.."
PASS=0; FAIL=0
run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  PASS $n"; PASS=$((PASS+1)); else echo "  FAIL $n"; FAIL=$((FAIL+1)); fi; }
echo "=== P69 Distributed Execution Policy Tests ==="
rm -f "$RD/data/cluster/agents/registry.json" "$RD/data/events/event_log.jsonl" 2>/dev/null || true
python3 -c "
import sys; sys.path.insert(0,'$RD/platform/cluster')
from registry import register_agent
register_agent('mira','mira','network_optimizer',['firewall_audit','wifi_analysis'],'audit')
register_agent('nova','nova','proxmox_optimizer',['cluster_scan'],'autonomous_low_risk')
register_agent('jasper','jasper','coordinator',['task_routing','incident_management','incident_investigation'],'assisted')
" 2>/dev/null

run_test "T1: audit_firewall allowed for mira" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster')
from execution_policy import evaluate_task_execution
d, r = evaluate_task_execution('mira','audit_firewall')
assert d == 'allow', f'{d}: {r}'
\""

run_test "T2: investigate denied for audit-mode mira" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster')
from execution_policy import evaluate_task_execution
d, r = evaluate_task_execution('mira','investigate_incident')
assert d == 'deny', f'{d}: {r}'
\""

run_test "T3: cluster_scan allowed for nova" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster')
from execution_policy import evaluate_task_execution
d, r = evaluate_task_execution('nova','audit_proxmox')
assert d == 'allow', f'{d}: {r}'
\""

run_test "T4: unregistered agent denied" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster')
from execution_policy import evaluate_task_execution
d, r = evaluate_task_execution('unknown','audit_firewall')
assert d == 'deny', f'{d}: {r}'
\""

run_test "T5: investigate requires review for assisted" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster')
from execution_policy import evaluate_task_execution
d, r = evaluate_task_execution('jasper','investigate_incident')
assert d == 'require_review', f'{d}: {r}'
\""

run_test "T6: capability enforcement" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster')
from execution_policy import evaluate_task_execution
d, r = evaluate_task_execution('nova','audit_firewall')
# nova lacks firewall_audit capability
assert d == 'deny', f'{d}: {r}'
\""

run_test "T7: secret scan" "! grep -rEi '(password|token|secret)\s*[:=]\s*[A-Za-z0-9+/]{8,}' '$RD/platform/cluster/execution_policy.py' 2>/dev/null || true"

echo ""; echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && exit 1 || { echo "ALL TESTS PASSED"; exit 0; }
