#!/usr/bin/env bash
# test_priority29_portfolio.sh — 10 acceptance tests for P29 Portfolio Publisher
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
LAB_ROOT="$ROOT_DIR/../../.."
PASS=0
FAIL=0
TOTAL=0

pass() { PASS=$((PASS+1)); TOTAL=$((TOTAL+1)); echo "  ✅ $1"; }
fail() { FAIL=$((FAIL+1)); TOTAL=$((TOTAL+1)); echo "  ❌ $1"; }

echo "=== P29 Portfolio Publisher Tests ==="

# Test 1: Policy file exists and valid
echo ""
echo "--- Test 1: Config ---"
[ -f "$ROOT_DIR/config/portfolio_policy.json" ] || { fail "portfolio_policy.json missing"; }
python3 -c "import json; json.load(open('$ROOT_DIR/config/portfolio_policy.json'))" 2>/dev/null \
    && pass "portfolio_policy.json valid" || fail "portfolio_policy.json invalid"

# Test 2: Redaction works
echo ""
echo "--- Test 2: Redaction ---"
python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
from portfolio_redact import redact_content
text = 'my key is sk-abcdefghijklmnopqrstuvwxyz and email test@example.com'
result, count = redact_content(text)
assert 'sk-REDACTED' in result, f'Token not redacted: {result}'
assert '[EMAIL REDACTED]' in result, f'Email not redacted: {result}'
assert count >= 2, f'Expected >=2 redactions, got {count}'
print('OK')
" 2>/dev/null && pass "Redaction strips tokens + emails" || fail "Redaction failed"

# Test 3: Site builds successfully
echo ""
echo "--- Test 3: Site build ---"
cd "$SCRIPT_DIR"
python3 portfolio_build.py 2>/dev/null && pass "Site builds without errors" || fail "Site build failed"

# Test 4: Index page exists
echo ""
echo "--- Test 4: Site content ---"
[ -f "$LAB_ROOT/site/docs/index.md" ] && pass "index.md exists" || fail "index.md missing"

# Test 5: Node pages exist
echo ""
echo "--- Test 5: Node pages ---"
ALL_NODES=true
for node in jasper nova mira orin; do
    [ -f "$LAB_ROOT/site/docs/nodes/$node.md" ] || { ALL_NODES=false; fail "$node.md missing"; }
done
$ALL_NODES && pass "All 4 node pages exist"

# Test 6: Mermaid diagram files generated
echo ""
echo "--- Test 6: Diagrams ---"
ALL_DIAG=true
for diag in topology.mmd services.mmd dependencies.mmd; do
    [ -f "$LAB_ROOT/site/docs/diagrams/$diag" ] || { ALL_DIAG=false; fail "$diag missing"; }
done
$ALL_DIAG && pass "All 3 Mermaid diagrams exist"

# Test 7: MkDocs config exists
echo ""
echo "--- Test 7: MkDocs ---"
[ -f "$LAB_ROOT/site/mkdocs.yml" ] && pass "mkdocs.yml exists" || fail "mkdocs.yml missing"

# Test 8: GitHub Pages workflow exists
echo ""
echo "--- Test 8: GitHub Actions ---"
[ -f "$LAB_ROOT/.github/workflows/portfolio_pages.yml" ] \
    && pass "portfolio_pages.yml workflow exists" || fail "workflow missing"

# Test 9: Pipeline pages exist
echo ""
echo "--- Test 9: Pipeline pages ---"
ALL_PIPE=true
for pipe in snapshots chaos planner actions evidence gatekeeper slo incidents; do
    [ -f "$LAB_ROOT/site/docs/pipelines/$pipe.md" ] || { ALL_PIPE=false; fail "$pipe.md missing"; }
done
$ALL_PIPE && pass "All 8 pipeline pages exist"

# Test 10: No secrets in site output
echo ""
echo "--- Test 10: Secret scan on site ---"
SECRETS=0
for pattern in "sk-[a-zA-Z]" "ghp_" "OPENAI_API_KEY" "BEGIN PRIVATE KEY"; do
    if grep -r "$pattern" "$LAB_ROOT/site/" 2>/dev/null | grep -v "test_priority29" | grep -v ".pyc"; then
        SECRETS=1
    fi
done
[ $SECRETS -eq 0 ] && pass "No secrets in site output" || fail "Secrets found in site!"

# Summary
echo ""
echo "==============================="
echo "P29 Portfolio Tests: $PASS/$TOTAL passed"
if [ $FAIL -gt 0 ]; then
    echo "❌ $FAIL test(s) failed"
    exit 1
else
    echo "✅ All tests passed"
fi
