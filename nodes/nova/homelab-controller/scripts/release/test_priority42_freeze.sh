#!/usr/bin/env bash
# P42 Acceptance Tests — System Freeze + Release v1.1 (10 tests)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
PASS=0; FAIL=0

run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  ✅ $n"; PASS=$((PASS+1)); else echo "  ❌ $n"; FAIL=$((FAIL+1)); fi; }

echo "=== P42 System Freeze + Release v1.1 Acceptance Tests ==="

run_test "Release notes v1.1 exist" \
    "test -f '$ROOT_DIR/release/v1.1/RELEASE_NOTES.md'"

run_test "System architecture v1.1 exists" \
    "test -f '$ROOT_DIR/release/v1.1/SYSTEM_ARCHITECTURE.md'"

run_test "Release notes mention P36-P41" \
    "grep -q 'P36' '$ROOT_DIR/release/v1.1/RELEASE_NOTES.md' && grep -q 'P41' '$ROOT_DIR/release/v1.1/RELEASE_NOTES.md'"

run_test "v1.1 tag script exists" \
    "test -f '$ROOT_DIR/scripts/release/release_tag_v11.sh'"

run_test "Tag script defaults to dry-run" \
    "grep -q 'Dry-run' '$ROOT_DIR/scripts/release/release_tag_v11.sh'"

run_test "Release audit script runs" \
    "python3 '$ROOT_DIR/scripts/release/release_audit.py'"

run_test "All P36-P41 config files exist" \
    "test -f '$ROOT_DIR/config/observability_policy.json' && test -f '$ROOT_DIR/config/infra_targets.json' && test -f '$ROOT_DIR/config/security_policy.json' && test -f '$ROOT_DIR/config/verification_policy.json' && test -f '$ROOT_DIR/config/supply_chain_policy.json'"

run_test "All P36-P41 test suites exist" \
    "test -f '$ROOT_DIR/scripts/obs/test_priority36_obs.sh' && test -f '$ROOT_DIR/scripts/infra/test_priority37_infra.sh' && test -f '$ROOT_DIR/scripts/sec/test_priority38_sec.sh' && test -f '$ROOT_DIR/scripts/portfolio/test_priority39_portfolio.sh' && test -f '$ROOT_DIR/scripts/verify/test_priority40_verify.sh' && test -f '$ROOT_DIR/scripts/supply/test_priority41_supply.sh'"

run_test "Dashboard has all panels" \
    "grep -q 'loadObs' '$ROOT_DIR/dashboard/static/index.html' && grep -q 'loadInfra' '$ROOT_DIR/dashboard/static/index.html' && grep -q 'loadSec' '$ROOT_DIR/dashboard/static/index.html' && grep -q 'loadVerify' '$ROOT_DIR/dashboard/static/index.html' && grep -q 'loadSupply' '$ROOT_DIR/dashboard/static/index.html' && grep -q 'loadPortfolio' '$ROOT_DIR/dashboard/static/index.html'"

run_test "Secret scan clean" \
    "! grep -rE 'AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36}|-----BEGIN.*PRIVATE KEY-----|sk-[a-zA-Z0-9]{48}' '$ROOT_DIR/release/v1.1/'*.md '$ROOT_DIR/scripts/release/release_tag_v11.sh'"

echo ""
echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && { echo "❌ SOME TESTS FAILED"; exit 1; } || { echo "✅ ALL TESTS PASSED"; exit 0; }
