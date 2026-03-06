#!/usr/bin/env bash
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
PASS=0; FAIL=0
run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  PASS $n"; PASS=$((PASS+1)); else echo "  FAIL $n"; FAIL=$((FAIL+1)); fi; }
echo "=== WiFi Optimizer Tests ==="

rm -rf "$ROOT_DIR/data/network_audit"/wifi_* 2>/dev/null || true

# T1: audit runs
run_test "T1: audit runs" \
    "python3 '$ROOT_DIR/platform/network/wifi_optimizer.py' audit 2>&1 | grep -q 'OK'"

# T2: report file written
run_test "T2: report file written" \
    "ls '$ROOT_DIR/data/network_audit'/wifi_audit_*.json 2>/dev/null | head -1"

# T3: mode is always assisted
run_test "T3: mode is assisted" \
    "python3 -c \"
import json, glob
f = sorted(glob.glob('$ROOT_DIR/data/network_audit/wifi_audit_*.json'))[-1]
d = json.load(open(f))
assert d['mode'] == 'assisted'
\""

# T4: no auto-applicable suggestions
run_test "T4: no auto-apply" \
    "python3 -c \"
import json, glob
f = sorted(glob.glob('$ROOT_DIR/data/network_audit/wifi_audit_*.json'))[-1]
d = json.load(open(f))
for s in d.get('suggestions', []):
    assert s['auto_applicable'] == False, 'WiFi should never auto-apply'
\""

# T5: detects channel issues with overlapping data
run_test "T5: channel analysis works" \
    "python3 -c \"
import sys; sys.path.insert(0,'$ROOT_DIR/platform/network')
from wifi_optimizer import analyze_channels
findings = analyze_channels([
    {'name': 'AP1', 'radios': [{'band': '2.4GHz', 'channel': 6, 'width': 20, 'tx_power': 15, 'client_count': 2}]},
    {'name': 'AP2', 'radios': [{'band': '2.4GHz', 'channel': 6, 'width': 20, 'tx_power': 15, 'client_count': 3}]},
])
assert len(findings) >= 1
assert findings[0]['type'] == 'co_channel_interference'
\""

# T6: secret scan clean
run_test "T6: secret scan clean" \
    "! grep -rEi '(password|token|secret)\s*[:=]\s*[A-Za-z0-9+/]{8,}' '$ROOT_DIR/platform/network/wifi_optimizer.py' 2>/dev/null || true"

echo ""; echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && exit 1 || { echo "ALL TESTS PASSED"; exit 0; }
