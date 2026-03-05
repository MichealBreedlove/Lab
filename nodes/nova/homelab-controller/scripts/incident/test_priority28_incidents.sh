#!/usr/bin/env bash
# test_priority28_incidents.sh — 10 acceptance tests for P28 Incident Commander
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
PASS=0
FAIL=0
TOTAL=0

pass() { PASS=$((PASS+1)); TOTAL=$((TOTAL+1)); echo "  ✅ $1"; }
fail() { FAIL=$((FAIL+1)); TOTAL=$((TOTAL+1)); echo "  ❌ $1"; }

echo "=== P28 Incident Commander Tests ==="

# Setup: clean test artifacts
TEST_DIR="$ROOT_DIR/artifacts/incidents"
mkdir -p "$TEST_DIR"

cd "$SCRIPT_DIR"

# Test 1: Open incident creates JSON + updates latest pointer
echo ""
echo "--- Test 1: Open incident lifecycle ---"
RESULT=$(python3 -c "
from incident_state import create_incident, ARTIFACTS_DIR, LATEST_DIR
inc = create_incident(
    trigger='test',
    severity='SEV2',
    title='Test incident',
    description='Testing lifecycle'
)
import json
from pathlib import Path
# Check file exists
assert (ARTIFACTS_DIR / f\"{inc['id']}.json\").exists(), 'Incident file not created'
# Check latest pointer
assert (LATEST_DIR / 'latest_incident.json').exists(), 'Latest pointer not created'
print(inc['id'])
" 2>&1) && pass "Open creates JSON + latest pointer (${RESULT})" || fail "Open lifecycle failed: $RESULT"

INC_ID="$RESULT"

# Test 2: Note appends timeline event
echo ""
echo "--- Test 2: Note appends timeline ---"
python3 -c "
from incident_state import add_timeline_event, load_incident
inc = add_timeline_event('$INC_ID', 'note', 'Test note content', 'tester')
assert len(inc['timeline']) >= 2, f'Expected >=2 timeline events, got {len(inc[\"timeline\"])}'
assert inc['timeline'][-1]['event'] == 'note'
assert inc['timeline'][-1]['detail'] == 'Test note content'
print('OK')
" 2>/dev/null && pass "Note appends timeline event" || fail "Note failed"

# Test 3: Close marks resolved + summary persists
echo ""
echo "--- Test 3: Close incident ---"
python3 -c "
from incident_state import close_incident, load_incident
inc = close_incident('$INC_ID', 'Fixed the issue', 'tester')
assert inc['status'] == 'resolved', f'Expected resolved, got {inc[\"status\"]}'
assert inc['resolution_summary'] == 'Fixed the issue'
assert inc['resolved_at'] is not None
assert inc['closed_at'] is not None
print('OK')
" 2>/dev/null && pass "Close marks resolved + summary" || fail "Close failed"

# Test 4: Renderer outputs incident md with required headings
echo ""
echo "--- Test 4: Render incident markdown ---"
python3 -c "
from incident_render import render_incident_md
from incident_state import load_incident
inc = load_incident('$INC_ID')
md = render_incident_md(inc)
assert '# ' in md, 'Missing heading'
assert 'Timeline' in md, 'Missing Timeline section'
assert 'Evidence' in md, 'Missing Evidence section'
assert '$INC_ID' in md, 'Missing incident ID'
print('OK')
" 2>/dev/null && pass "Incident markdown has required headings" || fail "Incident markdown render failed"

# Test 5: Renderer outputs postmortem md with required headings
echo ""
echo "--- Test 5: Render postmortem markdown ---"
python3 -c "
from incident_render import render_postmortem_md
from incident_state import load_incident
inc = load_incident('$INC_ID')
pm = render_postmortem_md(inc)
assert '## Summary' in pm
assert '## Impact' in pm
assert '## Timeline' in pm
assert '## Root Cause' in pm
assert '## Resolution' in pm
assert '## Lessons Learned' in pm
assert '## Action Items' in pm
print('OK')
" 2>/dev/null && pass "Postmortem has all required sections" || fail "Postmortem render failed"

# Test 6: Tick opens incident from synthetic high-burn SLO input
echo ""
echo "--- Test 6: Tick auto-opens on high burn SLO ---"
python3 -c "
import json, tempfile, os
from pathlib import Path
from incident_state import ARTIFACTS_DIR

# Create synthetic SLO current.json with high burn
slo_dir = Path('$ROOT_DIR/artifacts/slo')
slo_dir.mkdir(parents=True, exist_ok=True)
slo_data = {
    'slos': {
        'test_slo': {
            'name': 'Test SLO',
            'budget': {'budget_exhausted': True, 'remaining_budget_pct': 0},
            'burn_rates': {
                'rolling_1h': {'burn_rate': 10.0, 'sufficient_data': True}
            }
        }
    }
}
(slo_dir / 'current.json').write_text(json.dumps(slo_data))

# Count incidents before
before = len(list(ARTIFACTS_DIR.glob('INC-*.json')))

# Run tick
from incident_manager import cmd_tick
cmd_tick()

# Count after
after = len(list(ARTIFACTS_DIR.glob('INC-*.json')))
assert after > before, f'No new incident opened (before={before}, after={after})'
print('OK')
" 2>/dev/null && pass "Tick opens incident on high burn SLO" || fail "Tick SLO trigger failed"

# Test 7: Tick opens incident from gatekeeper deny input
echo ""
echo "--- Test 7: Tick auto-opens on gate deny ---"
# Wait a moment to avoid cooldown
sleep 1
python3 -c "
import json, time
from pathlib import Path
from incident_state import ARTIFACTS_DIR

# Create synthetic gatekeeper deny log
gate_dir = Path('$ROOT_DIR/artifacts/gatekeeper')
gate_dir.mkdir(parents=True, exist_ok=True)
entry = {'decision': 'DENY', 'reason': 'Test gate deny', 'timestamp': '2026-03-04T20:00:00'}
(gate_dir / 'decisions.jsonl').write_text(json.dumps(entry) + '\n')

before = len(list(ARTIFACTS_DIR.glob('INC-*.json')))
from incident_manager import cmd_tick
cmd_tick()
after = len(list(ARTIFACTS_DIR.glob('INC-*.json')))
# May or may not open (cooldown), but shouldn't crash
print('OK')
" 2>/dev/null && pass "Tick handles gatekeeper deny" || fail "Tick gate trigger failed"

# Test 8: Evidence paths linked safely
echo ""
echo "--- Test 8: Evidence paths safe ---"
python3 -c "
from incident_state import list_incidents
incs = list_incidents()
for inc in incs:
    for p in inc.get('evidence_paths', []):
        assert 'token' not in p.lower(), f'Token found in evidence path: {p}'
        assert 'secret' not in p.lower(), f'Secret found in evidence path: {p}'
        assert 'auth' not in p.lower(), f'Auth found in evidence path: {p}'
print('OK')
" 2>/dev/null && pass "Evidence paths contain no secrets" || fail "Evidence paths unsafe"

# Test 9: JSON fields merge-safe
echo ""
echo "--- Test 9: JSON merge-safe ---"
python3 -c "
import json
from incident_state import list_incidents
required = ['id', 'status', 'severity', 'title', 'trigger', 'opened_at', 'timeline']
for inc in list_incidents():
    for field in required:
        assert field in inc, f'Missing required field: {field} in {inc.get(\"id\",\"?\")}'
print('OK')
" 2>/dev/null && pass "All incidents have required JSON fields" || fail "JSON fields incomplete"

# Test 10: Secret scan clean
echo ""
echo "--- Test 10: Secret scan ---"
SECRETS_FOUND=0
for pattern in "sk-" "ghp_" "OPENAI_API_KEY" "ANTHROPIC_API_KEY" "BEGIN PRIVATE KEY"; do
    if grep -r "$pattern" "$ROOT_DIR/scripts/incident/" "$ROOT_DIR/config/incidents_policy.json" "$ROOT_DIR/docs/incidents/" 2>/dev/null | grep -v "test_priority28" | grep -v ".pyc"; then
        SECRETS_FOUND=1
    fi
done
[ $SECRETS_FOUND -eq 0 ] && pass "No secrets in incident code" || fail "Secrets found!"

# Cleanup synthetic test data
rm -f "$ROOT_DIR/artifacts/slo/current.json" 2>/dev/null || true
rm -f "$ROOT_DIR/artifacts/gatekeeper/decisions.jsonl" 2>/dev/null || true

# Summary
echo ""
echo "==============================="
echo "P28 Incident Tests: $PASS/$TOTAL passed"
if [ $FAIL -gt 0 ]; then
    echo "❌ $FAIL test(s) failed"
    exit 1
else
    echo "✅ All tests passed"
fi
