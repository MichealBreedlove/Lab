#!/usr/bin/env bash
# P39 Acceptance Tests — Recruiter Export Pack (10 tests)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
PASS=0; FAIL=0

run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  ✅ $n"; PASS=$((PASS+1)); else echo "  ❌ $n"; FAIL=$((FAIL+1)); fi; }

echo "=== P39 Recruiter Export Pack Acceptance Tests ==="

run_test "Portfolio renderer produces files" \
    "python3 '$SCRIPT_DIR/portfolio_render.py' --json | python3 -c 'import sys,json; d=json.load(sys.stdin); assert len(d.get(\"files\",[])) >= 3'"

run_test "PORTFOLIO_README.md generated" \
    "python3 '$SCRIPT_DIR/portfolio_render.py' && python3 -c \"
from pathlib import Path
root = Path('$ROOT_DIR').resolve().parents[2]
assert (root / '_meta' / 'PORTFOLIO_README.md').exists()
\""

run_test "CAPABILITIES.md generated" \
    "python3 -c \"
from pathlib import Path
root = Path('$ROOT_DIR').resolve().parents[2]
assert (root / '_meta' / 'CAPABILITIES.md').exists()
\""

run_test "OPERATIONS.md generated" \
    "python3 -c \"
from pathlib import Path
root = Path('$ROOT_DIR').resolve().parents[2]
assert (root / '_meta' / 'OPERATIONS.md').exists()
\""

run_test "SECURITY.md generated" \
    "python3 -c \"
from pathlib import Path
root = Path('$ROOT_DIR').resolve().parents[2]
assert (root / '_meta' / 'SECURITY.md').exists()
\""

run_test "Status publisher runs" \
    "python3 '$SCRIPT_DIR/portfolio_publish.py'"

run_test "Status JSON generated" \
    "test -f '$ROOT_DIR/dashboard/static/data/portfolio_status.json'"

run_test "README contains architecture table" \
    "python3 -c \"
from pathlib import Path
root = Path('$ROOT_DIR').resolve().parents[2]
content = (root / '_meta' / 'PORTFOLIO_README.md').read_text()
assert 'Jasper' in content and 'Nova' in content
\""

run_test "CAPABILITIES mentions all subsystems" \
    "python3 -c \"
from pathlib import Path
root = Path('$ROOT_DIR').resolve().parents[2]
content = (root / '_meta' / 'CAPABILITIES.md').read_text()
assert 'SLO' in content and 'Chaos' in content and 'AI' in content
\""

run_test "Secret scan clean" \
    "! grep -rE 'AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36}|-----BEGIN.*PRIVATE KEY-----|sk-[a-zA-Z0-9]{48}' '$SCRIPT_DIR'/*.py"

echo ""
echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && { echo "❌ SOME TESTS FAILED"; exit 1; } || { echo "✅ ALL TESTS PASSED"; exit 0; }
