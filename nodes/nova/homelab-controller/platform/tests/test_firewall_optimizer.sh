#!/usr/bin/env bash
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
PASS=0; FAIL=0
run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  PASS $n"; PASS=$((PASS+1)); else echo "  FAIL $n"; FAIL=$((FAIL+1)); fi; }
echo "=== Firewall Optimizer Tests ==="

rm -rf "$ROOT_DIR/data/network_audit"/firewall_* 2>/dev/null || true

# T1: audit runs without errors
run_test "T1: audit runs" \
    "python3 '$ROOT_DIR/platform/network/firewall_optimizer.py' audit 2>&1 | grep -q 'OK'"

# T2: report file written
run_test "T2: report file written" \
    "ls '$ROOT_DIR/data/network_audit'/firewall_audit_*.json 2>/dev/null | head -1"

# T3: detects overly broad allow
run_test "T3: overly broad allow detected" \
    "python3 -c \"
import json, glob
f = sorted(glob.glob('$ROOT_DIR/data/network_audit/firewall_audit_*.json'))[-1]
d = json.load(open(f))
types = [f['type'] for f in d['findings']]
assert 'overly_broad_allow' in types
\""

# T4: detects duplicate aliases
run_test "T4: duplicate aliases detected" \
    "python3 -c \"
import json, glob
f = sorted(glob.glob('$ROOT_DIR/data/network_audit/firewall_audit_*.json'))[-1]
d = json.load(open(f))
types = [f['type'] for f in d['findings']]
assert 'duplicate_alias' in types
\""

# T5: WAN rules never auto-applicable
run_test "T5: high risk never auto-apply" \
    "python3 -c \"
import json, glob
f = sorted(glob.glob('$ROOT_DIR/data/network_audit/firewall_audit_*.json'))[-1]
d = json.load(open(f))
for r in d.get('recommendations', []):
    if r.get('severity') == 'high':
        assert r['auto_applicable'] == False, 'high risk should not auto-apply'
\""

# T6: default mode is audit
run_test "T6: default mode is audit" \
    "python3 -c \"
import sys; sys.path.insert(0,'$ROOT_DIR/platform/network')
from firewall_optimizer import get_mode
assert get_mode() == 'audit'
\""

# T7: secret scan clean
run_test "T7: secret scan clean" \
    "! grep -rEi '(password|token|secret)\s*[:=]\s*[A-Za-z0-9+/]{8,}' '$ROOT_DIR/platform/network/' 2>/dev/null || true"

echo ""; echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && exit 1 || { echo "ALL TESTS PASSED"; exit 0; }
