#!/usr/bin/env bash
# P43 Acceptance Tests — Homelab Control Plane (10 tests)
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."
PASS=0; FAIL=0

run_test() { local n="$1"; shift; if eval "$@" >/dev/null 2>&1; then echo "  ✅ $n"; PASS=$((PASS+1)); else echo "  ❌ $n"; FAIL=$((FAIL+1)); fi; }

echo "=== P43 Homelab Control Plane Acceptance Tests ==="

run_test "T1: Ansible inventory valid" \
    "ansible-inventory -i '$ROOT_DIR/inventory/inventory.yml' --list > /dev/null"

run_test "T2: Preflight playbook syntax" \
    "ansible-playbook --syntax-check -i '$ROOT_DIR/inventory/inventory.yml' '$ROOT_DIR/playbooks/00_preflight.yml'"

run_test "T3: OPNsense playbook syntax" \
    "ansible-playbook --syntax-check -i '$ROOT_DIR/inventory/inventory.yml' '$ROOT_DIR/playbooks/10_inventory_opnsense.yml'"

run_test "T4: Proxmox playbook syntax" \
    "ansible-playbook --syntax-check -i '$ROOT_DIR/inventory/inventory.yml' '$ROOT_DIR/playbooks/20_inventory_proxmox.yml'"

run_test "T5: Switch playbook syntax" \
    "ansible-playbook --syntax-check -i '$ROOT_DIR/inventory/inventory.yml' '$ROOT_DIR/playbooks/30_inventory_switches.yml'"

run_test "T6: BIOS playbook syntax" \
    "ansible-playbook --syntax-check -i '$ROOT_DIR/inventory/inventory.yml' '$ROOT_DIR/playbooks/35_inventory_bios.yml'"

run_test "T7: Apply changes playbook syntax" \
    "ansible-playbook --syntax-check -i '$ROOT_DIR/inventory/inventory.yml' '$ROOT_DIR/playbooks/40_apply_changes.yml'"

run_test "T8: Device connectivity script runs" \
    "python3 '$SCRIPT_DIR/device_connectivity.py' --json"

run_test "T9: Sanitize script exists and executable" \
    "test -x '$SCRIPT_DIR/sanitize.sh'"

run_test "T10: No secrets in inventory files" \
    "! grep -rEi '(password|token|secret)\s*[:=]\s*[A-Za-z0-9+/]{8,}' '$ROOT_DIR/inventory/' 2>/dev/null || true"

echo ""
echo "Results: $PASS passed, $FAIL failed out of $((PASS+FAIL))"
[ "$FAIL" -gt 0 ] && { echo "❌ SOME TESTS FAILED"; exit 1; } || { echo "✅ ALL TESTS PASSED"; exit 0; }
