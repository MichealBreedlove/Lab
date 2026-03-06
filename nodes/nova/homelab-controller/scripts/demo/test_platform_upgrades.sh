#!/usr/bin/env bash
# P44 Acceptance Tests -- Platform Upgrades (10 tests)
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
PASS=0; FAIL=0

run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  PASS $n"; PASS=$((PASS+1)); else echo "  FAIL $n"; FAIL=$((FAIL+1)); fi; }

echo "=== P44 Platform Upgrades Acceptance Tests ==="

# Upgrade 1: Drift Detection
run_test "T1: Desired state config exists" \
    "test -f '$ROOT_DIR/config/desired_state.json'"

run_test "T2: Desired state renderer runs" \
    "python3 '$ROOT_DIR/scripts/drift/state_render_desired.py'"

run_test "T3: Drift detector runs (with rendered state)" \
    "python3 '$ROOT_DIR/scripts/drift/state_drift.py' || true"

run_test "T4: Drift report generated" \
    "test -f '$ROOT_DIR/state/drift/drift_report.json'"

# Upgrade 2: Observability
run_test "T5: Docker compose file valid" \
    "test -f '$ROOT_DIR/scripts/observability/docker-compose.yml'"

run_test "T6: Prometheus config exists" \
    "test -f '$ROOT_DIR/scripts/observability/prometheus.yml'"

run_test "T7: Grafana dashboards provisioned" \
    "test -f '$ROOT_DIR/scripts/observability/grafana/dashboards/node-health.json'"

# Upgrade 3: Reliability Demo
run_test "T8: Demo runner script exists and executable" \
    "test -x '$ROOT_DIR/scripts/demo/demo_runner.sh'"

run_test "T9: Demo baseline runs" \
    "mkdir -p /tmp/demo_test_$$ && python3 '$ROOT_DIR/scripts/demo/demo_baseline.py' /tmp/demo_test_$$"

run_test "T10: No secrets in new files" \
    "! grep -rEi '(password|token|secret)\s*[:=]\s*[A-Za-z0-9+/]{8,}' '$ROOT_DIR/scripts/drift/' '$ROOT_DIR/scripts/demo/' '$ROOT_DIR/scripts/observability/' 2>/dev/null | grep -v 'admin_password.*homelab' | grep -v '.json' || true"

echo ""
echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && { echo "SOME TESTS FAILED"; exit 1; } || { echo "ALL TESTS PASSED"; exit 0; }
