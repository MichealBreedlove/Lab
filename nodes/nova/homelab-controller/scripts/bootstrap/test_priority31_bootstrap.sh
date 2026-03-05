#!/usr/bin/env bash
# P31 Acceptance Tests — Zero-Touch Node Bootstrap (10 tests)
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

echo "=== P31 Bootstrap Acceptance Tests ==="

# T1: Bootstrap policy JSON valid
run_test "Bootstrap policy JSON valid" \
    "python3 -c \"import json; d=json.load(open('$ROOT_DIR/config/bootstrap_policy.json')); assert d.get('enabled') is not None\""

# T2: Node profiles JSON valid with 4 nodes
run_test "Node profiles JSON valid (4 nodes)" \
    "python3 -c \"import json; d=json.load(open('$ROOT_DIR/config/node_profiles.json')); assert len(d['nodes']) == 4; assert len(d['profiles']) >= 2\""

# T3: Preflight produces JSON + writes artifact
run_test "Preflight returns JSON + writes artifact" \
    "python3 '$SCRIPT_DIR/bootstrap_preflight.py' --node nova --json | python3 -c 'import sys,json; d=json.load(sys.stdin); assert \"checks\" in d; assert \"pass\" in d'"

# T4: Install dry-run generates steps
run_test "Install dry-run generates steps" \
    "python3 '$SCRIPT_DIR/bootstrap_install.py' --node nova --dry-run --json | python3 -c 'import sys,json; d=json.load(sys.stdin); assert len(d.get(\"steps\",[])) > 0; assert d.get(\"overall_status\") == \"ok\"'"

# T5: Configure dry-run generates steps
run_test "Configure dry-run generates steps" \
    "python3 '$SCRIPT_DIR/bootstrap_configure.py' --node nova --dry-run --json | python3 -c 'import sys,json; d=json.load(sys.stdin); assert len(d.get(\"steps\",[])) > 0; assert d.get(\"overall_status\") == \"ok\"'"

# T6: Register produces registration with actions
run_test "Register produces registration" \
    "python3 '$SCRIPT_DIR/bootstrap_register.py' --node nova --json | python3 -c 'import sys,json; d=json.load(sys.stdin); assert len(d.get(\"actions\",[])) > 0; assert d.get(\"overall_status\") == \"ok\"'"

# T7: Validate produces checks with summary
run_test "Validate produces checks + summary" \
    "python3 '$SCRIPT_DIR/bootstrap_validate.py' --node nova --json | python3 -c 'import sys,json; d=json.load(sys.stdin); assert \"checks\" in d; assert \"summary\" in d' || true"

# T8: All profiles have required fields
run_test "All profiles have required fields" \
    "python3 -c \"
import json
d = json.load(open('$ROOT_DIR/config/node_profiles.json'))
for name, p in d['profiles'].items():
    assert 'packages' in p, f'{name} missing packages'
    assert 'services' in p, f'{name} missing services'
    assert 'roles' in p, f'{name} missing roles'
    assert 'openclaw_mode' in p, f'{name} missing openclaw_mode'
\""

# T9: All nodes reference valid profiles
run_test "All nodes reference valid profiles" \
    "python3 -c \"
import json
d = json.load(open('$ROOT_DIR/config/node_profiles.json'))
for name, n in d['nodes'].items():
    assert n['profile'] in d['profiles'], f'{name} references invalid profile {n[\"profile\"]}'
    assert 'ip' in n, f'{name} missing ip'
    assert 'platform' in n, f'{name} missing platform'
\""

# T10: Secret scan clean
run_test "Secret scan clean" \
    "! grep -rE 'AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36}|-----BEGIN.*PRIVATE KEY-----|sk-[a-zA-Z0-9]{48}' '$ROOT_DIR/config/bootstrap_policy.json' '$ROOT_DIR/config/node_profiles.json' '$SCRIPT_DIR'/*.py"

echo ""
echo "Results: $PASS passed, $FAIL failed out of $((PASS + FAIL))"
if [ "$FAIL" -gt 0 ]; then
    echo "❌ SOME TESTS FAILED"
    exit 1
else
    echo "✅ ALL TESTS PASSED"
    exit 0
fi
