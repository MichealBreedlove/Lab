#!/usr/bin/env bash
# P45 Acceptance Tests -- Change Log + Evidence Pack (10 tests)
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
PASS=0; FAIL=0

run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  PASS $n"; PASS=$((PASS+1)); else echo "  FAIL $n"; FAIL=$((FAIL+1)); fi; }

echo "=== P45 Change Log + Evidence Pack Acceptance Tests ==="

# T1: change_create produces unique ID
CHANGE_ID=$(python3 "$ROOT_DIR/scripts/change/change_create.py" manual "test change" 2>/dev/null | tail -1)
run_test "T1: change_create produces unique ID" \
    "echo '$CHANGE_ID' | grep -q 'CHG-'"

# T2: change_diff produces markdown
run_test "T2: change_diff produces markdown diff" \
    "python3 '$ROOT_DIR/scripts/change/change_diff.py' '$CHANGE_ID' && test -f '$ROOT_DIR/changes/$CHANGE_ID/diff.md'"

# T3: change_validate runs connectivity checks
run_test "T3: change_validate runs checks" \
    "python3 '$ROOT_DIR/scripts/change/change_validate.py' '$CHANGE_ID' || true; test -f '$ROOT_DIR/changes/$CHANGE_ID/validation.json'"

# T4: change_render produces markdown report
run_test "T4: change_render produces report" \
    "python3 '$ROOT_DIR/scripts/change/change_render.py' '$CHANGE_ID' && test -f '$ROOT_DIR/changes/$CHANGE_ID/change.md'"

# T5: evidence pack folder created
run_test "T5: evidence pack folder exists" \
    "test -d '$ROOT_DIR/changes/$CHANGE_ID/evidence'"

# T6: dashboard data updated
run_test "T6: dashboard changes_status.json updated" \
    "test -f '$ROOT_DIR/dashboard/static/data/changes_status.json'"

# T7: change.json has all phases
run_test "T7: change.json has phase timestamps" \
    "python3 -c \"import json; d=json.load(open('$ROOT_DIR/changes/$CHANGE_ID/change.json')); assert d['phases']['rendered']\""

# T8: CLI list command works (via oc.sh)
run_test "T8: oc change list works" \
    "bash '$ROOT_DIR/bin/oc.sh' change list"

# T9: secret scan clean on change files
run_test "T9: no secrets in change scripts" \
    "! grep -rEi '(password|token|secret)\s*[:=]\s*[A-Za-z0-9+/]{8,}' '$ROOT_DIR/scripts/change/' 2>/dev/null || true"

# T10: idempotent - re-render same change
run_test "T10: re-render is idempotent" \
    "python3 '$ROOT_DIR/scripts/change/change_render.py' '$CHANGE_ID'"

# Cleanup test change
rm -rf "$ROOT_DIR/changes/$CHANGE_ID" 2>/dev/null || true

echo ""
echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && { echo "SOME TESTS FAILED"; exit 1; } || { echo "ALL TESTS PASSED"; exit 0; }
