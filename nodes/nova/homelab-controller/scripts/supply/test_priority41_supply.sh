#!/usr/bin/env bash
# P41 Acceptance Tests — Hardening + Supply Chain (10 tests)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
PASS=0; FAIL=0

run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  ✅ $n"; PASS=$((PASS+1)); else echo "  ❌ $n"; FAIL=$((FAIL+1)); fi; }

echo "=== P41 Hardening + Supply Chain Acceptance Tests ==="

run_test "Supply chain policy valid" \
    "python3 -c \"import json; d=json.load(open('$ROOT_DIR/config/supply_chain_policy.json')); assert d.get('enabled')\""

run_test "SBOM config has scan dirs" \
    "python3 -c \"import json; d=json.load(open('$ROOT_DIR/config/supply_chain_policy.json')); assert len(d['sbom']['scan_dirs']) >= 2\""

run_test "SBOM generator runs" \
    "python3 '$SCRIPT_DIR/supply_sbom.py'"

run_test "SBOM JSON generated" \
    "test -f '$ROOT_DIR/artifacts/supply_chain/sbom.json'"

run_test "Provenance recorder runs" \
    "python3 '$SCRIPT_DIR/supply_provenance.py'"

run_test "Provenance JSON generated" \
    "test -f '$ROOT_DIR/artifacts/supply_chain/provenance.json'"

run_test "Hardening checker runs" \
    "python3 '$SCRIPT_DIR/supply_harden.py'"

run_test "Status publisher runs" \
    "python3 '$SCRIPT_DIR/supply_publish.py'"

run_test "Status JSON generated" \
    "test -f '$ROOT_DIR/dashboard/static/data/supply_status.json'"

run_test "Secret scan clean" \
    "! grep -rE 'AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36}|-----BEGIN.*PRIVATE KEY-----|sk-[a-zA-Z0-9]{48}' '$ROOT_DIR/config/supply_chain_policy.json' '$SCRIPT_DIR'/*.py"

echo ""
echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && { echo "❌ SOME TESTS FAILED"; exit 1; } || { echo "✅ ALL TESTS PASSED"; exit 0; }
