#!/usr/bin/env bash
# test_priority27_slo.sh — Tests for P27 SLO pipeline
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/.."
PASS=0
FAIL=0
TOTAL=0

pass() { PASS=$((PASS+1)); TOTAL=$((TOTAL+1)); echo "  ✅ $1"; }
fail() { FAIL=$((FAIL+1)); TOTAL=$((TOTAL+1)); echo "  ❌ $1"; }

echo "=== P27 SLO Tests ==="

# Test 1: Config files exist
echo ""
echo "--- Config files ---"
[ -f "$ROOT_DIR/config/slo_policy.json" ] && pass "slo_policy.json exists" || fail "slo_policy.json missing"
[ -f "$ROOT_DIR/config/slo_catalog.json" ] && pass "slo_catalog.json exists" || fail "slo_catalog.json missing"

# Test 2: Policy is valid JSON
echo ""
echo "--- Config validity ---"
python3 -c "import json; json.load(open('$ROOT_DIR/config/slo_policy.json'))" 2>/dev/null \
    && pass "slo_policy.json is valid JSON" || fail "slo_policy.json invalid JSON"
python3 -c "import json; json.load(open('$ROOT_DIR/config/slo_catalog.json'))" 2>/dev/null \
    && pass "slo_catalog.json is valid JSON" || fail "slo_catalog.json invalid JSON"

# Test 3: Policy has required fields
echo ""
echo "--- Policy structure ---"
python3 -c "
import json
p = json.load(open('$ROOT_DIR/config/slo_policy.json'))
assert 'enabled' in p, 'missing enabled'
assert 'windows' in p, 'missing windows'
assert 'burn_thresholds' in p, 'missing burn_thresholds'
assert 'gating_integration' in p, 'missing gating_integration'
print('OK')
" 2>/dev/null && pass "Policy has required fields" || fail "Policy missing required fields"

# Test 4: Catalog has SLOs defined
python3 -c "
import json
c = json.load(open('$ROOT_DIR/config/slo_catalog.json'))
slos = c.get('slos', [])
assert len(slos) >= 4, f'Expected >=4 SLOs, got {len(slos)}'
for s in slos:
    assert 'id' in s, 'SLO missing id'
    assert 'objective' in s, 'SLO missing objective'
    assert 'sli_type' in s, 'SLO missing sli_type'
    assert 'good_event' in s, 'SLO missing good_event'
print('OK')
" 2>/dev/null && pass "Catalog has >=4 well-formed SLOs" || fail "Catalog SLO validation failed"

# Test 5: Python scripts exist
echo ""
echo "--- Script files ---"
for script in sli_sources.py sli_compute.py budget.py burn_rate.py slo_eval.py slo_render.py slo_publish.py slo_utils.py; do
    [ -f "$ROOT_DIR/scripts/slo/$script" ] && pass "$script exists" || fail "$script missing"
done
[ -f "$ROOT_DIR/scripts/slo_runner.py" ] && pass "slo_runner.py exists" || fail "slo_runner.py missing"

# Test 6: Python imports work
echo ""
echo "--- Import tests ---"
cd "$ROOT_DIR/scripts/slo"
python3 -c "from slo_utils import load_policy, load_catalog; print('OK')" 2>/dev/null \
    && pass "slo_utils imports OK" || fail "slo_utils import failed"
python3 -c "from sli_sources import load_all_events; print('OK')" 2>/dev/null \
    && pass "sli_sources imports OK" || fail "sli_sources import failed"
python3 -c "from sli_compute import compute_slis_for_catalog; print('OK')" 2>/dev/null \
    && pass "sli_compute imports OK" || fail "sli_compute import failed"
python3 -c "from budget import compute_all_budgets; print('OK')" 2>/dev/null \
    && pass "budget imports OK" || fail "budget import failed"
python3 -c "from burn_rate import compute_all_burn_rates; print('OK')" 2>/dev/null \
    && pass "burn_rate imports OK" || fail "burn_rate import failed"
python3 -c "from slo_eval import evaluate_all; print('OK')" 2>/dev/null \
    && pass "slo_eval imports OK" || fail "slo_eval import failed"
python3 -c "from slo_render import render_markdown_report; print('OK')" 2>/dev/null \
    && pass "slo_render imports OK" || fail "slo_render import failed"

# Test 7: Burn rate math
echo ""
echo "--- Burn rate math ---"
python3 -c "
from burn_rate import compute_burn_rate
# 99% objective, observing 98% => burn rate should be 2.0x
br = compute_burn_rate(0.98, 0.99)
assert abs(br - 2.0) < 0.01, f'Expected 2.0, got {br}'
# 99% objective, observing 99% => burn rate 1.0x
br = compute_burn_rate(0.99, 0.99)
assert abs(br - 1.0) < 0.01, f'Expected 1.0, got {br}'
# 99.9% objective, observing 99% => burn rate 10x
br = compute_burn_rate(0.99, 0.999)
assert abs(br - 10.0) < 0.01, f'Expected 10.0, got {br}'
print('OK')
" 2>/dev/null && pass "Burn rate calculations correct" || fail "Burn rate math wrong"

# Test 8: Budget computation
echo ""
echo "--- Budget computation ---"
python3 -c "
from budget import compute_budget
slo = {'id': 'test', 'objective': 0.99}
events = [{'timestamp': '2026-03-04T12:00:00', 'good': True}] * 98 + \
         [{'timestamp': '2026-03-04T12:00:00', 'good': False}] * 2
result = compute_budget(slo, events, budget_window_days=28)
assert result['total_events'] == 100
assert result['good_events'] == 98
assert result['bad_events'] == 2
assert result['allowed_bad_events'] == 1.0
assert result['consumed_budget_pct'] == 200.0  # 2x over budget
assert result['budget_exhausted'] == True
print('OK')
" 2>/dev/null && pass "Budget computation correct" || fail "Budget computation wrong"

# Summary
echo ""
echo "==============================="
echo "P27 SLO Tests: $PASS/$TOTAL passed"
if [ $FAIL -gt 0 ]; then
    echo "❌ $FAIL test(s) failed"
    exit 1
else
    echo "✅ All tests passed"
fi
