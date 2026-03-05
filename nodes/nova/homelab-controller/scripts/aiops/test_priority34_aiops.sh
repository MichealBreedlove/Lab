#!/usr/bin/env bash
# P34 Acceptance Tests — AI Operations Layer (10 tests)
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

echo "=== P34 AI Operations Layer Acceptance Tests ==="

# T1: AIOps policy JSON valid
run_test "AIOps policy JSON valid" \
    "python3 -c \"import json; d=json.load(open('$ROOT_DIR/config/aiops_policy.json')); assert d.get('enabled') is not None; assert 'ollama' in d\""

# T2: Anomaly detector loads and produces valid structure
run_test "Anomaly detector produces valid JSON" \
    "python3 '$SCRIPT_DIR/aiops_anomaly.py' --json | python3 -c 'import sys,json; d=json.load(sys.stdin); assert \"anomalies\" in d; assert \"timestamp\" in d'"

# T3: Correlator produces valid structure
run_test "Correlator produces valid JSON" \
    "python3 '$SCRIPT_DIR/aiops_correlate.py' --json | python3 -c 'import sys,json; d=json.load(sys.stdin); assert \"incidents\" in d; assert \"total_events\" in d'"

# T4: Analyzer runs without LLM (fallback mode)
run_test "Analyzer runs in no-LLM mode" \
    "python3 '$SCRIPT_DIR/aiops_analyze.py' --no-llm --json | python3 -c 'import sys,json; d=json.load(sys.stdin); assert \"analysis\" in d'"

# T5: Report generator produces markdown
run_test "Report generator produces markdown" \
    "python3 '$SCRIPT_DIR/aiops_report.py' --json | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d.get(\"file\")'"

# T6: Z-score computation is correct
run_test "Z-score computation correct" \
    "python3 -c \"
import sys, math; sys.path.insert(0, '$SCRIPT_DIR')
from aiops_anomaly import compute_stats
mean, std = compute_stats([10, 20, 30, 40, 50])
assert abs(mean - 30.0) < 0.01, f'mean={mean}'
assert abs(std - math.sqrt(250)) < 0.01, f'std={std}'
\""

# T7: Anomaly detection config has required fields
run_test "Anomaly detection config complete" \
    "python3 -c \"
import json
d = json.load(open('$ROOT_DIR/config/aiops_policy.json'))
ad = d['anomaly_detection']
assert 'z_score_threshold' in ad
assert 'min_samples' in ad
assert 'metrics' in ad
assert len(ad['metrics']) >= 3
\""

# T8: Incident correlation config complete
run_test "Incident correlation config complete" \
    "python3 -c \"
import json
d = json.load(open('$ROOT_DIR/config/aiops_policy.json'))
ic = d['incident_correlation']
assert 'time_window_minutes' in ic
assert 'min_events_to_correlate' in ic
\""

# T9: Ollama config present (endpoint, model)
run_test "Ollama config present" \
    "python3 -c \"
import json
d = json.load(open('$ROOT_DIR/config/aiops_policy.json'))
o = d['ollama']
assert 'endpoint' in o
assert 'model' in o
assert 'timeout_sec' in o
\""

# T10: Secret scan clean
run_test "Secret scan clean" \
    "! grep -rE 'AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36}|-----BEGIN.*PRIVATE KEY-----|sk-[a-zA-Z0-9]{48}' '$ROOT_DIR/config/aiops_policy.json' '$SCRIPT_DIR'/*.py"

echo ""
echo "Results: $PASS passed, $FAIL failed out of $((PASS + FAIL))"
if [ "$FAIL" -gt 0 ]; then
    echo "❌ SOME TESTS FAILED"
    exit 1
else
    echo "✅ ALL TESTS PASSED"
    exit 0
fi
