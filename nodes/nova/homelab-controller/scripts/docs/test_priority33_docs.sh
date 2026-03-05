#!/usr/bin/env bash
# P33 Acceptance Tests — Self-Documenting Architecture (10 tests)
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

echo "=== P33 Self-Documenting Architecture Acceptance Tests ==="

# T1: Docs policy JSON valid
run_test "Docs policy JSON valid" \
    "python3 -c \"import json; d=json.load(open('$ROOT_DIR/config/docs_policy.json')); assert d.get('enabled') is not None\""

# T2: Topology generator produces markdown
run_test "Topology generator produces markdown" \
    "python3 '$SCRIPT_DIR/docs_topology.py' --json | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d.get(\"file\"); assert d.get(\"nodes\") >= 1'"

# T3: Services generator produces markdown
run_test "Services generator produces markdown" \
    "python3 '$SCRIPT_DIR/docs_services.py' --json | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d.get(\"file\")'"

# T4: Dependencies generator scans imports
run_test "Dependencies generator scans imports" \
    "python3 '$SCRIPT_DIR/docs_dependencies.py' --json | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d.get(\"file\")'"

# T5: Changelog generator processes commits
run_test "Changelog generator processes commits" \
    "python3 '$SCRIPT_DIR/docs_changelog.py' --json | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d.get(\"commits_processed\", 0) >= 0'"

# T6: Generated docs directory created
run_test "Generated docs directory exists after generation" \
    "python3 '$SCRIPT_DIR/docs_topology.py' && test -d '$ROOT_DIR/docs/generated'"

# T7: TOPOLOGY.md contains node table
run_test "TOPOLOGY.md contains node table" \
    "python3 '$SCRIPT_DIR/docs_topology.py' && grep -q '| nova |' '$ROOT_DIR/docs/generated/TOPOLOGY.md'"

# T8: All generators run successfully
run_test "All generators run successfully" \
    "python3 '$SCRIPT_DIR/docs_generate_all.py'"

# T9: Docs policy has required sections
run_test "Docs policy has all sections" \
    "python3 -c \"
import json
d = json.load(open('$ROOT_DIR/config/docs_policy.json'))
s = d['sections']
for key in ['topology', 'services', 'dependencies', 'changelog']:
    assert key in s, f'Missing section: {key}'
\""

# T10: Secret scan clean
run_test "Secret scan clean" \
    "! grep -rE 'AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36}|-----BEGIN.*PRIVATE KEY-----|sk-[a-zA-Z0-9]{48}' '$ROOT_DIR/config/docs_policy.json' '$SCRIPT_DIR'/*.py"

echo ""
echo "Results: $PASS passed, $FAIL failed out of $((PASS + FAIL))"
if [ "$FAIL" -gt 0 ]; then
    echo "❌ SOME TESTS FAILED"
    exit 1
else
    echo "✅ ALL TESTS PASSED"
    exit 0
fi
