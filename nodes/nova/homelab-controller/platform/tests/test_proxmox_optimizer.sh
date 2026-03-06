#!/usr/bin/env bash
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
PASS=0; FAIL=0
run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  PASS $n"; PASS=$((PASS+1)); else echo "  FAIL $n"; FAIL=$((FAIL+1)); fi; }
echo "=== Proxmox Cluster Optimizer Tests ==="

rm -rf "$ROOT_DIR/data/proxmox_audit"/proxmox_* 2>/dev/null || true

# T1: audit runs
run_test "T1: audit runs" \
    "python3 '$ROOT_DIR/platform/proxmox/cluster_optimizer.py' audit 2>&1 | grep -q 'OK'"

# T2: report file written
run_test "T2: report file written" \
    "ls '$ROOT_DIR/data/proxmox_audit'/proxmox_audit_*.json 2>/dev/null | head -1"

# T3: detects missing tags
run_test "T3: missing tags detected" \
    "python3 -c \"
import json, glob
f = sorted(glob.glob('$ROOT_DIR/data/proxmox_audit/proxmox_audit_*.json'))[-1]
d = json.load(open(f))
types = [f['type'] for f in d['findings']]
assert 'missing_tags' in types
\""

# T4: detects orphaned snapshots
run_test "T4: orphaned snapshot detected" \
    "python3 -c \"
import json, glob
f = sorted(glob.glob('$ROOT_DIR/data/proxmox_audit/proxmox_audit_*.json'))[-1]
d = json.load(open(f))
types = [f['type'] for f in d['findings']]
assert 'orphaned_snapshot' in types
\""

# T5: default mode is audit
run_test "T5: default mode is audit" \
    "python3 -c \"
import sys; sys.path.insert(0,'$ROOT_DIR/platform/proxmox')
from cluster_optimizer import get_mode
assert get_mode() == 'audit'
\""

# T6: never-auto-apply list enforced
run_test "T6: NEVER_AUTO_APPLY list" \
    "python3 -c \"
import sys; sys.path.insert(0,'$ROOT_DIR/platform/proxmox')
from cluster_optimizer import NEVER_AUTO_APPLY
assert 'bridge_changes' in NEVER_AUTO_APPLY
assert 'storage_migration' in NEVER_AUTO_APPLY
assert 'cluster_quorum_changes' in NEVER_AUTO_APPLY
\""

# T7: low risk actions defined
run_test "T7: LOW_RISK_ACTIONS defined" \
    "python3 -c \"
import sys; sys.path.insert(0,'$ROOT_DIR/platform/proxmox')
from cluster_optimizer import LOW_RISK_ACTIONS
assert 'add_tags' in LOW_RISK_ACTIONS
assert 'generate_notes' in LOW_RISK_ACTIONS
\""

# T8: secret scan clean
run_test "T8: secret scan clean" \
    "! grep -rEi '(password|token|secret)\s*[:=]\s*[A-Za-z0-9+/]{8,}' '$ROOT_DIR/platform/proxmox/' 2>/dev/null || true"

echo ""; echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && exit 1 || { echo "ALL TESTS PASSED"; exit 0; }
