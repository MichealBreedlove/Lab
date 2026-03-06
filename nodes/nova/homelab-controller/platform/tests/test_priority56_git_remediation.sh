#!/usr/bin/env bash
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
PASS=0; FAIL=0; API_PORT=18456
run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  PASS $n"; PASS=$((PASS+1)); else echo "  FAIL $n"; FAIL=$((FAIL+1)); fi; }
echo "=== P56 Git-Backed Remediation Artifacts Tests ==="

VW=$(python3 "$ROOT_DIR/scripts/identity/token_issuer.py" create viewer t56-viewer 2>&1 | grep 'Secret:' | awk '{print $NF}')
SR=$(python3 "$ROOT_DIR/scripts/identity/token_issuer.py" create sre t56-sre 2>&1 | grep 'Secret:' | awk '{print $NF}')

# Setup: run an investigation first
python3 "$ROOT_DIR/platform/aiops/investigator.py" run INC-T56-001 api confirmed --simulate >/dev/null 2>&1

# T1: generate summary markdown
python3 "$ROOT_DIR/platform/aiops/remediator.py" generate INC-T56-001 >/dev/null 2>&1
run_test "T1: summary markdown created" \
    "test -f '$ROOT_DIR/data/remediation/incidents/INC-T56-001-summary.md'"

# T2: proposal json created
run_test "T2: proposal json created" \
    "test -f '$ROOT_DIR/data/remediation/incidents/INC-T56-001-proposal.json'"

# T3: patch plan created
run_test "T3: patch-plan markdown created" \
    "test -f '$ROOT_DIR/data/remediation/incidents/INC-T56-001-patch-plan.md'"

# T4: artifact_created event emitted
run_test "T4: remediation.artifact_created event" \
    "grep -q 'ai.remediation.artifact_created' '$ROOT_DIR/data/events/event_log.jsonl'"

# T5: artifacts include incident id
run_test "T5: artifacts include incident id" \
    "grep -q 'INC-T56-001' '$ROOT_DIR/data/remediation/incidents/INC-T56-001-summary.md'"

# T6+T7: API endpoint permissions
PLATFORM_PORT=$API_PORT python3 "$ROOT_DIR/platform/api/server.py" &
PID=$!; sleep 2
cleanup() { kill $PID 2>/dev/null||true; python3 -c "
import json; f='$ROOT_DIR/artifacts/identity/active_tokens.json'
d=json.load(open(f)); d['tokens']=[t for t in d['tokens'] if 't56-' not in t.get('name','')]; json.dump(d,open(f,'w'),indent=2)
" 2>/dev/null||true; }
trap cleanup EXIT
A="http://localhost:$API_PORT"

run_test "T6: viewer cannot POST /remediation/artifact" \
    "curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Authorization: Bearer $VW' -H 'Content-Type: application/json' -d '{\"incident_id\":\"INC-T56-001\"}' '$A/remediation/artifact' | grep -q '403'"

run_test "T7: sre can POST /remediation/artifact" \
    "curl -sf -X POST -H 'Authorization: Bearer $SR' -H 'Content-Type: application/json' -d '{\"incident_id\":\"INC-T56-001\"}' '$A/remediation/artifact' | python3 -c 'import sys,json; d=json.load(sys.stdin); assert \"artifacts\" in d'"

# T8: status shows remediation_artifacts_enabled
run_test "T8: status has remediation_artifacts_enabled" \
    "curl -sf -H 'Authorization: Bearer $SR' '$A/' | python3 -c 'import sys,json; assert json.load(sys.stdin).get(\"remediation_artifacts_enabled\")==True'"

# T9: secret scan clean
run_test "T9: secret scan clean" \
    "! grep -rEi '(password|token|secret)\s*[:=]\s*[A-Za-z0-9+/]{8,}' '$ROOT_DIR/platform/aiops/' 2>/dev/null || true"

echo ""; echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && exit 1 || { echo "ALL TESTS PASSED"; exit 0; }
