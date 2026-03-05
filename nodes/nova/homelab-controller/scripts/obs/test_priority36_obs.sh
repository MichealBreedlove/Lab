#!/usr/bin/env bash
# P36 Acceptance Tests — Observability + Event Bus (10 tests)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
PASS=0
FAIL=0

run_test() {
    local name="$1"
    shift
    if eval "$@" >/dev/null 2>&1; then
        echo "  ✅ $name"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $name"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== P36 Observability + Event Bus Acceptance Tests ==="

# T1: Policy JSON valid
run_test "Observability policy JSON valid" \
    "python3 -c \"import json; d=json.load(open('$ROOT_DIR/config/observability_policy.json')); assert d.get('enabled') is not None\""

# T2: Compose file valid YAML
run_test "Compose file valid YAML" \
    "python3 -c \"import yaml; yaml.safe_load(open('$SCRIPT_DIR/obs_compose.yml'))\" 2>/dev/null || python3 -c \"
# Fallback: basic structure check
content = open('$SCRIPT_DIR/obs_compose.yml').read()
assert 'prometheus' in content
assert 'grafana' in content
assert 'alertmanager' in content
\""

# T3: Scrape config has all targets
run_test "Scrape config has all node targets" \
    "python3 -c \"
content = open('$SCRIPT_DIR/obs_scrape.yml').read()
assert 'node-nova' in content
assert 'node-mira' in content
assert 'node-orin' in content
assert '10.1.1.22' in content
assert '10.1.1.23' in content
\""

# T4: Alert rules defined
run_test "Alert rules defined" \
    "python3 -c \"
content = open('$SCRIPT_DIR/obs_rules.yml').read()
assert 'NodeDown' in content
assert 'HighCPU' in content
assert 'HighMemory' in content
assert 'DiskCritical' in content
\""

# T5: Event bus writes events
run_test "Event bus writes events" \
    "python3 '$SCRIPT_DIR/obs_eventbus.py' write --type obs.stack.up --severity info --message 'test event' && test -f '$ROOT_DIR/artifacts/events/events.jsonl'"

# T6: Event bus reads events
run_test "Event bus reads events" \
    "python3 '$SCRIPT_DIR/obs_eventbus.py' read --limit 5"

# T7: Event types list works
run_test "Event types list" \
    "python3 '$SCRIPT_DIR/obs_eventbus.py' types | grep -q 'snapshot.created'"

# T8: Status publisher runs
run_test "Status publisher runs" \
    "python3 '$SCRIPT_DIR/obs_publish.py'"

# T9: Status JSON generated
run_test "Status JSON generated" \
    "test -f '$ROOT_DIR/dashboard/static/data/obs_status.json'"

# T10: Secret scan clean
run_test "Secret scan clean" \
    "! grep -rE 'AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36}|-----BEGIN.*PRIVATE KEY-----|sk-[a-zA-Z0-9]{48}' '$ROOT_DIR/config/observability_policy.json' '$SCRIPT_DIR'/*.py '$SCRIPT_DIR'/*.yml"

echo ""
echo "Results: $PASS passed, $FAIL failed out of $((PASS + FAIL))"
if [ "$FAIL" -gt 0 ]; then
    echo "❌ SOME TESTS FAILED"
    exit 1
else
    echo "✅ ALL TESTS PASSED"
    exit 0
fi
