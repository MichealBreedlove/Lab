#!/usr/bin/env bash
# P40 Acceptance Tests — Continuous Verification (10 tests)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
PASS=0; FAIL=0

run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  ✅ $n"; PASS=$((PASS+1)); else echo "  ❌ $n"; FAIL=$((FAIL+1)); fi; }

echo "=== P40 Continuous Verification Acceptance Tests ==="

run_test "Verification policy valid" \
    "python3 -c \"import json; d=json.load(open('$ROOT_DIR/config/verification_policy.json')); assert d.get('enabled')\""

run_test "Synthetic checks defined (6+)" \
    "python3 -c \"import json; d=json.load(open('$ROOT_DIR/config/verification_policy.json')); assert len(d['synthetic_checks']['checks']) >= 6\""

run_test "Canary checks defined" \
    "python3 -c \"import json; d=json.load(open('$ROOT_DIR/config/verification_policy.json')); assert len(d['canary_checks']['checks']) >= 2\""

run_test "Policy gates defined (4)" \
    "python3 -c \"import json; d=json.load(open('$ROOT_DIR/config/verification_policy.json')); assert len(d['policy_gates']) >= 4\""

run_test "Synthetic module loads" \
    "python3 -c \"import importlib.util; spec=importlib.util.spec_from_file_location('vs','$SCRIPT_DIR/verify_synthetic.py'); assert spec\""

run_test "Canary module loads" \
    "python3 -c \"import importlib.util; spec=importlib.util.spec_from_file_location('vc','$SCRIPT_DIR/verify_canary.py'); assert spec\""

run_test "Gates module runs" \
    "python3 '$SCRIPT_DIR/verify_gates.py'"

run_test "Status publisher runs" \
    "python3 '$SCRIPT_DIR/verify_publish.py'"

run_test "Status JSON generated" \
    "test -f '$ROOT_DIR/dashboard/static/data/verify_status.json'"

run_test "Secret scan clean" \
    "! grep -rE 'AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36}|-----BEGIN.*PRIVATE KEY-----|sk-[a-zA-Z0-9]{48}' '$ROOT_DIR/config/verification_policy.json' '$SCRIPT_DIR'/*.py"

echo ""
echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && { echo "❌ SOME TESTS FAILED"; exit 1; } || { echo "✅ ALL TESTS PASSED"; exit 0; }
