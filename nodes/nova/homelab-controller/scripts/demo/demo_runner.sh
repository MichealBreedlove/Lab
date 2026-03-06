#!/usr/bin/env bash
# One-Command Reliability Demo Runner
# Usage: demo_runner.sh <scenario>
# Scenarios: gateway_restart_outage, ollama_unreachable
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
SCENARIO="${1:?Usage: demo_runner.sh <scenario>}"
TIMESTAMP=$(date +%Y-%m-%dT%H%M%S)
DEMO_DIR="$ROOT_DIR/artifacts/demos/$SCENARIO/$TIMESTAMP"

mkdir -p "$DEMO_DIR"

log() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$DEMO_DIR/demo.log"; }

log "=== Reliability Demo: $SCENARIO ==="
log "Output: $DEMO_DIR"

# Phase 1: Pre-check baseline
log ""
log "--- Phase 1: Baseline ---"
python3 "$SCRIPT_DIR/demo_baseline.py" "$DEMO_DIR" 2>&1 | tee -a "$DEMO_DIR/demo.log"

# Phase 2: Inject chaos
log ""
log "--- Phase 2: Chaos Injection ---"
python3 "$SCRIPT_DIR/demo_chaos.py" "$SCENARIO" "$DEMO_DIR" 2>&1 | tee -a "$DEMO_DIR/demo.log"

# Phase 3: Detect failure
log ""
log "--- Phase 3: Failure Detection ---"
python3 "$SCRIPT_DIR/demo_detect.py" "$SCENARIO" "$DEMO_DIR" 2>&1 | tee -a "$DEMO_DIR/demo.log"

# Phase 4: Remediate
log ""
log "--- Phase 4: Remediation ---"
python3 "$SCRIPT_DIR/demo_remediate.py" "$SCENARIO" "$DEMO_DIR" 2>&1 | tee -a "$DEMO_DIR/demo.log"

# Phase 5: Validate recovery
log ""
log "--- Phase 5: Validation ---"
python3 "$SCRIPT_DIR/demo_validate.py" "$SCENARIO" "$DEMO_DIR" 2>&1 | tee -a "$DEMO_DIR/demo.log"

# Phase 6: Generate evidence + postmortem
log ""
log "--- Phase 6: Evidence Pack ---"
python3 "$SCRIPT_DIR/demo_evidence.py" "$SCENARIO" "$DEMO_DIR" "$TIMESTAMP" 2>&1 | tee -a "$DEMO_DIR/demo.log"

log ""
log "=== Demo complete: $SCENARIO ==="
log "Evidence: $DEMO_DIR"
