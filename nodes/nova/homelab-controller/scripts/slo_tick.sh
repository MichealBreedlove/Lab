#!/usr/bin/env bash
# slo_tick.sh — Cron/timer entry point for SLO evaluation
# Usage: bash slo_tick.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "=== SLO tick @ $(date -Iseconds) ==="

python3 scripts/slo_runner.py
EXIT_CODE=$?

if [ $EXIT_CODE -eq 2 ]; then
    echo "⚠️  SLO budget exhausted detected"
elif [ $EXIT_CODE -eq 1 ]; then
    echo "⚠️  SLO budget at risk detected"
else
    echo "✅ All SLOs healthy"
fi

exit $EXIT_CODE
