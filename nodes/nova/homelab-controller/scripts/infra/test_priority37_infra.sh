#!/usr/bin/env bash
# P37 Acceptance Tests — Infrastructure Control Plane (10 tests)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
PASS=0
FAIL=0

run_test() {
    local name="$1"; shift
    if eval "$@" >/dev/null 2>&1; then
        echo "  ✅ $name"; PASS=$((PASS + 1))
    else
        echo "  ❌ $name"; FAIL=$((FAIL + 1))
    fi
}

echo "=== P37 Infrastructure Control Plane Acceptance Tests ==="

run_test "Infra targets JSON valid" \
    "python3 -c \"import json; d=json.load(open('$ROOT_DIR/config/infra_targets.json')); assert 'opnsense' in d; assert 'proxmox' in d; assert 'nodes' in d\""

run_test "Infra targets has 4 nodes" \
    "python3 -c \"import json; d=json.load(open('$ROOT_DIR/config/infra_targets.json')); assert len(d['nodes']) == 4\""

run_test "Infra targets has 3 Proxmox hosts" \
    "python3 -c \"import json; d=json.load(open('$ROOT_DIR/config/infra_targets.json')); assert len(d['proxmox']['hosts']) == 3\""

run_test "Inventory module loads" \
    "python3 -c \"import importlib.util; spec=importlib.util.spec_from_file_location('ii','$SCRIPT_DIR/infra_inventory.py'); assert spec\""

run_test "Proxmox export module loads" \
    "python3 -c \"import importlib.util; spec=importlib.util.spec_from_file_location('pe','$SCRIPT_DIR/proxmox_export.py'); assert spec\""

run_test "OPNsense backup module loads" \
    "python3 -c \"import importlib.util; spec=importlib.util.spec_from_file_location('ob','$SCRIPT_DIR/opnsense_backup.py'); assert spec\""

run_test "Status publisher runs" \
    "python3 '$SCRIPT_DIR/infra_publish.py'"

run_test "Status JSON generated" \
    "test -f '$ROOT_DIR/dashboard/static/data/infra_status.json'"

run_test "Switch backup placeholders exist" \
    "test -d '$SCRIPT_DIR/switch_backup_placeholders'"

run_test "Secret scan clean" \
    "! grep -rE 'AKIA[0-9A-Z]{16}|ghp_[a-zA-Z0-9]{36}|-----BEGIN.*PRIVATE KEY-----|sk-[a-zA-Z0-9]{48}' '$ROOT_DIR/config/infra_targets.json' '$SCRIPT_DIR'/*.py"

echo ""
echo "Results: $PASS passed, $FAIL failed out of $((PASS + FAIL))"
[ "$FAIL" -gt 0 ] && { echo "❌ SOME TESTS FAILED"; exit 1; } || { echo "✅ ALL TESTS PASSED"; exit 0; }
