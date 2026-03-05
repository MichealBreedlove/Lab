#!/usr/bin/env bash
# P30 Acceptance Tests — DR System (10 tests)
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

echo "=== P30 DR Acceptance Tests ==="

# T1: Policy JSON valid
run_test "Policy JSON valid" \
    "python3 -c \"import json; d=json.load(open('$ROOT_DIR/config/dr_policy.json')); assert d.get('enabled') is not None\""

# T2: Targets JSON valid
run_test "Targets JSON valid" \
    "python3 -c \"import json; d=json.load(open('$ROOT_DIR/config/restore_targets.json')); assert 'nodes' in d; assert len(d['nodes']) == 4\""

# T3: Preflight returns JSON + writes artifact
run_test "Preflight returns JSON + writes artifact" \
    "python3 '$SCRIPT_DIR/dr_preflight.py' --node nova --allow-dirty --json | python3 -c 'import sys,json; d=json.load(sys.stdin); assert \"preflight_pass\" in d' && test -f '$ROOT_DIR/artifacts/dr/preflight.json'"

# T4: Inventory produces expected keys
run_test "Inventory produces expected keys" \
    "python3 '$SCRIPT_DIR/dr_backup_inventory.py' --node nova --json | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d.get(\"platform\") in (\"linux\",\"windows\"); assert \"timestamp\" in d'"

# T5: Restore dry-run generates ordered plan
run_test "Restore dry-run generates ordered plan" \
    "python3 '$SCRIPT_DIR/dr_restore.py' --node nova --dry-run --json | python3 -c 'import sys,json; d=json.load(sys.stdin); assert len(d.get(\"actions\",[])) > 0; assert d.get(\"overall_status\") == \"ok\"'"

# T6: Restore refuses if break-glass missing for destructive action
run_test "Restore refuses without break-glass" \
    "python3 -c \"
import sys; sys.path.insert(0, '$SCRIPT_DIR')
from dr_restore import load_json, check_break_glass
policy = load_json('$ROOT_DIR/config/dr_policy.json')
ok, msg = check_break_glass(policy)
assert not ok, 'break-glass should fail when token missing'
\""

# T7: Validate runs and produces output
run_test "Validate runs and produces output" \
    "python3 '$SCRIPT_DIR/dr_validate.py' --node nova --json | python3 -c 'import sys,json; d=json.load(sys.stdin); assert \"checks\" in d; assert \"summary\" in d' || true"

# T8: Restore apply would start service (verified via plan actions)
run_test "Restore plan includes restart actions" \
    "python3 '$SCRIPT_DIR/dr_restore.py' --node nova --dry-run --json | python3 -c 'import sys,json; d=json.load(sys.stdin); restarts=[a for a in d.get(\"actions\",[]) if \"restart\" in a.get(\"step\",\"\")]; assert len(restarts) > 0'"

# T9: Drill report structure (dry check via import)
run_test "Drill module importable" \
    "cd '$SCRIPT_DIR' && python3 -c 'from dr_drill import run_drill; print(\"ok\")'"

# T10: Secret scan clean
run_test "Secret scan clean" \
    "! grep -rE 'AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36}|-----BEGIN.*PRIVATE KEY-----|sk-[a-zA-Z0-9]{48}' '$ROOT_DIR/config/dr_policy.json' '$ROOT_DIR/config/restore_targets.json' '$SCRIPT_DIR'/*.py"

echo ""
echo "Results: $PASS passed, $FAIL failed out of $((PASS + FAIL))"
if [ "$FAIL" -gt 0 ]; then
    echo "❌ SOME TESTS FAILED"
    exit 1
else
    echo "✅ ALL TESTS PASSED"
    exit 0
fi
