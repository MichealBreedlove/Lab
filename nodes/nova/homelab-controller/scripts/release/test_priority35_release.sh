#!/usr/bin/env bash
# P35 Acceptance Tests — System Freeze + Release (10 tests)
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

echo "=== P35 System Freeze + Release Acceptance Tests ==="

# T1: Release audit passes
run_test "Release audit passes" \
    "python3 '$SCRIPT_DIR/release_audit.py' --json | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d.get(\"pass\") == True, \"Audit failed\"'"

# T2: All subsystem configs present
run_test "All subsystem configs present" \
    "python3 -c \"
from pathlib import Path
root = Path('$ROOT_DIR')
configs = ['dr_policy.json', 'bootstrap_policy.json', 'node_profiles.json',
           'capacity_policy.json', 'docs_policy.json', 'aiops_policy.json']
for c in configs:
    assert (root / 'config' / c).exists(), f'Missing: {c}'
\""

# T3: Release docs generated
run_test "Release docs generated" \
    "python3 '$SCRIPT_DIR/release_build_docs.py' --json | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d.get(\"count\") >= 3'"

# T4: Release notes exist
run_test "Release notes exist" \
    "test -f '$ROOT_DIR/release/v1.0/RELEASE_NOTES.md'"

# T5: Restore guide exists
run_test "Restore guide exists" \
    "test -f '$ROOT_DIR/release/v1.0/RESTORE_GUIDE.md'"

# T6: System architecture doc exists
run_test "System architecture doc exists" \
    "test -f '$ROOT_DIR/release/v1.0/SYSTEM_ARCHITECTURE.md'"

# T7: Release manifest valid
run_test "Release manifest valid" \
    "python3 '$SCRIPT_DIR/release_package.py' --json | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d.get(\"version\") == \"1.0.0\"; assert d.get(\"all_subsystems_present\")'"

# T8: All script directories exist
run_test "All script directories exist" \
    "python3 -c \"
from pathlib import Path
root = Path('$ROOT_DIR')
dirs = ['scripts/dr', 'scripts/bootstrap', 'scripts/capacity', 'scripts/docs', 'scripts/aiops', 'scripts/release']
for d in dirs:
    assert (root / d).exists(), f'Missing: {d}'
\""

# T9: Dashboard file exists
run_test "Dashboard file exists" \
    "test -f '$ROOT_DIR/dashboard/static/index.html'"

# T10: Secret scan clean
run_test "Secret scan clean" \
    "python3 '$SCRIPT_DIR/release_audit.py' --json | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d[\"checks\"][\"secrets\"][\"pass\"] == True'"

echo ""
echo "Results: $PASS passed, $FAIL failed out of $((PASS + FAIL))"
if [ "$FAIL" -gt 0 ]; then
    echo "❌ SOME TESTS FAILED"
    exit 1
else
    echo "✅ ALL TESTS PASSED"
    exit 0
fi
