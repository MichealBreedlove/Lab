#!/usr/bin/env bash
# P38 Acceptance Tests — Security Hygiene (10 tests)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
PASS=0; FAIL=0

run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  ✅ $n"; PASS=$((PASS+1)); else echo "  ❌ $n"; FAIL=$((FAIL+1)); fi; }

echo "=== P38 Security Hygiene Acceptance Tests ==="

run_test "Security policy JSON valid" \
    "python3 -c \"import json; d=json.load(open('$ROOT_DIR/config/security_policy.json')); assert d.get('enabled')\""

run_test "Redaction patterns defined" \
    "python3 -c \"import json; d=json.load(open('$ROOT_DIR/config/security_policy.json')); assert len(d.get('redaction_patterns',[])) >= 4\""

run_test "SSH baseline defined" \
    "python3 -c \"import json; d=json.load(open('$ROOT_DIR/config/security_policy.json')); assert 'permit_root_login' in d.get('ssh_baseline',{})\""

run_test "Audit module loads" \
    "python3 -c \"import importlib.util; spec=importlib.util.spec_from_file_location('sa','$SCRIPT_DIR/sec_baseline_audit.py'); assert spec\""

run_test "Redaction library works" \
    "python3 -c \"import sys; sys.path.insert(0,'$SCRIPT_DIR'); from sec_redact import redact; assert 'REDACTED' in redact('password=mysecret123')\""

run_test "Secret scanner runs clean" \
    "python3 '$SCRIPT_DIR/sec_secretscan.py'"

run_test "Status publisher runs" \
    "python3 '$SCRIPT_DIR/sec_publish.py'"

run_test "Status JSON generated" \
    "test -f '$ROOT_DIR/dashboard/static/data/sec_status.json'"

run_test "Allowed ports defined" \
    "python3 -c \"import json; d=json.load(open('$ROOT_DIR/config/security_policy.json')); assert len(d.get('allowed_ports',{})) >= 5\""

run_test "No real secrets in configs" \
    "! grep -rE 'AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36}|sk-[a-zA-Z0-9]{48}' '$ROOT_DIR/config/security_policy.json'"

echo ""
echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && { echo "❌ SOME TESTS FAILED"; exit 1; } || { echo "✅ ALL TESTS PASSED"; exit 0; }
