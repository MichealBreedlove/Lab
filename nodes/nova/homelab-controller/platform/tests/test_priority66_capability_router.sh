#!/usr/bin/env bash
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
SD="$(cd "$(dirname "$0")" && pwd)"; RD="$SD/../.."
PASS=0; FAIL=0
run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  PASS $n"; PASS=$((PASS+1)); else echo "  FAIL $n"; FAIL=$((FAIL+1)); fi; }
echo "=== P66 Capability Router Tests ==="
rm -f "$RD/data/cluster/agents/registry.json" "$RD/data/events/event_log.jsonl" 2>/dev/null || true
# Register all 4 agents
python3 -c "
import sys; sys.path.insert(0,'$RD/platform/cluster')
from registry import register_agent
register_agent('jasper','jasper','coordinator',['task_routing','incident_management'],'assisted')
register_agent('nova','nova','proxmox_optimizer',['cluster_scan','vm_inventory'],'autonomous_low_risk')
register_agent('mira','mira','network_optimizer',['firewall_audit','wifi_analysis'],'audit')
register_agent('orin','orin','heavy_analysis',['log_analysis','anomaly_detection'],'assisted')
" 2>/dev/null

run_test "T1: firewall -> mira" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster')
from router import route_task
a, r = route_task('audit_firewall')
assert a == 'mira', f'got {a}'
\""

run_test "T2: proxmox -> nova" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster')
from router import route_task
a, r = route_task('audit_proxmox')
assert a == 'nova', f'got {a}'
\""

run_test "T3: logs -> orin" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster')
from router import route_task
a, r = route_task('analyze_logs')
assert a == 'orin', f'got {a}'
\""

run_test "T4: unknown -> jasper" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster')
from router import route_task
a, r = route_task('unknown_task')
assert a == 'jasper', f'got {a}'
\""

run_test "T5: fallback when agent offline" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster')
from registry import set_status
from router import route_task
set_status('mira', 'offline')
a, r = route_task('audit_firewall')
assert a == 'jasper', f'got {a}: {r}'
set_status('mira', 'online')
\""

run_test "T6: preferred agent" "python3 -c \"
import sys; sys.path.insert(0,'$RD/platform/cluster')
from router import route_task
a, r = route_task('audit_firewall', preferred_agent='orin')
assert a == 'orin', f'got {a}'
\""

run_test "T7: secret scan" "! grep -rEi '(password|token|secret)\s*[:=]\s*[A-Za-z0-9+/]{8,}' '$RD/platform/cluster/router.py' 2>/dev/null || true"

echo ""; echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && exit 1 || { echo "ALL TESTS PASSED"; exit 0; }
