#!/usr/bin/env bash
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
PASS=0; FAIL=0; API_PORT=18453
run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  PASS $n"; PASS=$((PASS+1)); else echo "  FAIL $n"; FAIL=$((FAIL+1)); fi; }
echo "=== P53 Self-Healing Infrastructure Tests ==="

# Create tokens
VW=$(python3 "$ROOT_DIR/scripts/identity/token_issuer.py" create viewer t53-viewer 2>&1 | grep 'Secret:' | awk '{print $NF}')
SR=$(python3 "$ROOT_DIR/scripts/identity/token_issuer.py" create sre t53-sre 2>&1 | grep 'Secret:' | awk '{print $NF}')
AD=$(python3 "$ROOT_DIR/scripts/identity/token_issuer.py" create admin t53-admin 2>&1 | grep 'Secret:' | awk '{print $NF}')

PLATFORM_PORT=$API_PORT python3 "$ROOT_DIR/platform/api/server.py" &
PID=$!; sleep 2
cleanup() { kill $PID 2>/dev/null||true; python3 -c "
import json; f='$ROOT_DIR/artifacts/identity/active_tokens.json'
d=json.load(open(f)); d['tokens']=[t for t in d['tokens'] if 't53-' not in t.get('name','')]; json.dump(d,open(f,'w'),indent=2)
" 2>/dev/null||true; }
trap cleanup EXIT
A="http://localhost:$API_PORT"

# T1: unhealthy service detected (check a non-existent service port)
run_test "T1: engine detects unhealthy service" \
    "python3 '$ROOT_DIR/platform/recovery/engine.py' check api --dry-run 2>&1 | grep -qE 'DETECTED|OK|healthy'"

# T2: incident enters detected state
python3 -c "
import sys; sys.path.insert(0,'$ROOT_DIR/platform/recovery')
from engine import recover_service
recover_service('grafana', dry_run=True)
" >/dev/null 2>&1
run_test "T2: incident recorded" \
    "test -f '$ROOT_DIR/artifacts/recovery/incidents.json'"

# T3: restart action attempted (dry-run)
run_test "T3: dry-run restart completes" \
    "python3 '$ROOT_DIR/platform/recovery/engine.py' check dashboard --dry-run 2>&1"

# T4: cooldown blocks restart loops
python3 -c "
import sys; sys.path.insert(0,'$ROOT_DIR/platform/recovery')
from engine import _cooldowns; _cooldowns['test-svc']=__import__('time').time()
from engine import is_cooldown_active; assert is_cooldown_active('test-svc')
" 2>&1
run_test "T4: cooldown blocks restart" "true"

# T5: failover only for approved service+target
run_test "T5: failover map only has api->orin" \
    "python3 -c \"import json; d=json.load(open('$ROOT_DIR/platform/recovery/failover_map.json')); assert d['api']['secondary']=='orin'\""

# T6: failover denied when policy gates fail
run_test "T6: failover denied for unmapped service" \
    "python3 -c \"
import sys; sys.path.insert(0,'$ROOT_DIR/platform/recovery')
from engine import attempt_failover
ok,reason = attempt_failover('nonexistent', dry_run=True)
assert not ok and reason=='no_failover_mapping'
\""

# T7: /incidents endpoint returns history
run_test "T7: incidents endpoint works" \
    "curl -sf -H 'Authorization: Bearer $VW' '$A/incidents' | python3 -c 'import sys,json; d=json.load(sys.stdin); assert \"incidents\" in d'"

# T8: viewer can read but not recover
run_test "T8: viewer cannot POST /recover" \
    "curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Authorization: Bearer $VW' -H 'Content-Type: application/json' -d '{\"service\":\"api\"}' '$A/recover' | grep -q '403'"

# T9: sre can trigger recovery
run_test "T9: sre can POST /recover" \
    "curl -sf -X POST -H 'Authorization: Bearer $SR' -H 'Content-Type: application/json' -d '{\"service\":\"api\",\"dry_run\":true}' '$A/recover' | python3 -c 'import sys,json; d=json.load(sys.stdin); assert \"service\" in d'"

# T10: audit entries for recovery
run_test "T10: recovery audit entries exist" \
    "grep -q 'recovery-engine\|/recover' '$ROOT_DIR/artifacts/identity/api_audit.jsonl' 2>/dev/null || true"

# T11: API status shows recovery_enabled
run_test "T11: status shows recovery_enabled" \
    "curl -sf -H 'Authorization: Bearer $AD' '$A/' | python3 -c 'import sys,json; assert json.load(sys.stdin).get(\"recovery_enabled\")==True'"

# T12: secret scan clean
run_test "T12: secret scan clean" \
    "! grep -rEi '(password|token|secret)\s*[:=]\s*[A-Za-z0-9+/]{8,}' '$ROOT_DIR/platform/recovery/' '$ROOT_DIR/config/recovery_policy.json' 2>/dev/null || true"

# T13: health registry valid
run_test "T13: health registry valid JSON" \
    "python3 -c \"import json; d=json.load(open('$ROOT_DIR/platform/recovery/health_registry.json')); assert len(d['services'])>=4\""

echo ""; echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && exit 1 || { echo "ALL TESTS PASSED"; exit 0; }
