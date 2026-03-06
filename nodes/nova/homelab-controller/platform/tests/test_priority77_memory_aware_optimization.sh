#!/usr/bin/env bash
# P77 — Memory-Aware Infrastructure Optimization tests
set -euo pipefail
cd "$(dirname "$0")/../.."
PASS=0; FAIL=0
check() { if eval "$2"; then echo "  [PASS] $1"; ((PASS++)); else echo "  [FAIL] $1"; ((FAIL++)); fi; }

echo "=== P77: Memory-Aware Infrastructure Optimization ==="

# T1: firewall_optimizer has memory integration
check "firewall_optimizer has memory code" "grep -q '_query_memory_for_recommendations\|memory_history' platform/network/firewall_optimizer.py"

# T2: wifi_optimizer has memory integration
check "wifi_optimizer has memory code" "grep -q '_query_wifi_memory\|memory_history' platform/network/wifi_optimizer.py"

# T3: cluster_optimizer has memory integration
check "cluster_optimizer has memory code" "grep -q '_query_proxmox_memory\|memory_history' platform/proxmox/cluster_optimizer.py"

# T4: firewall audit still runs with no memory data
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/network')
from firewall_optimizer import run_audit
report = run_audit()
print(report['finding_count'] >= 0)
")
check "firewall audit runs without memory" "[ '$RESULT' = 'True' ]"

# T5: wifi audit still runs with no memory data
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/network')
from wifi_optimizer import run_audit
report = run_audit()
print(report['finding_count'] >= 0)
")
check "wifi audit runs without memory" "[ '$RESULT' = 'True' ]"

# T6: proxmox audit still runs with no memory data
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/proxmox')
from cluster_optimizer import run_audit
report = run_audit()
print(report['finding_count'] >= 0)
")
check "proxmox audit runs without memory" "[ '$RESULT' = 'True' ]"

# T7: suppression works for repeatedly rejected recommendations
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory'); sys.path.insert(0,'platform/network')
from store import store_memory
# Seed 3 rejected optimization memories for duplicate_alias
for i in range(3):
    store_memory('optimization', 'mira', {'finding':'duplicate_alias','outcome':'rejected'}, tags=['firewall','duplicate_alias'])
from firewall_optimizer import generate_recommendations
findings = [{'type':'duplicate_alias','severity':'low','detail':'test','category':'aliases'}]
recs = generate_recommendations(findings)
suppressed = any(r.get('action') == 'suppressed_by_memory' for r in recs)
print(suppressed)
")
check "repeatedly rejected recommendations suppressed" "[ '$RESULT' = 'True' ]"

# T8: memory boost works for accepted recommendations
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory'); sys.path.insert(0,'platform/network')
from store import store_memory
for i in range(2):
    store_memory('optimization', 'mira', {'finding':'stale_dhcp_lease','outcome':'accepted'}, tags=['firewall','stale_dhcp_lease'])
from firewall_optimizer import generate_recommendations
findings = [{'type':'stale_dhcp_lease','severity':'low','detail':'test','category':'dhcp'}]
recs = generate_recommendations(findings)
boosted = any(r.get('memory_boost') for r in recs)
print(boosted)
")
check "accepted recommendations get memory boost" "[ '$RESULT' = 'True' ]"

# T9: memory never overrides safety policy
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory'); sys.path.insert(0,'platform/network')
from store import store_memory
for i in range(5):
    store_memory('optimization', 'mira', {'finding':'overly_broad_allow','outcome':'accepted'}, tags=['firewall','overly_broad_allow'])
from firewall_optimizer import generate_recommendations
findings = [{'type':'overly_broad_allow','severity':'high','detail':'any->any pass','category':'wan_rules'}]
recs = generate_recommendations(findings)
# High severity + NEVER_AUTO_APPLY should still require manual review
print(recs[0]['action'] == 'manual_review_required' and not recs[0].get('auto_applicable', False))
")
check "memory cannot override safety for high-severity" "[ '$RESULT' = 'True' ]"

# T10: memory_history field present in recommendations when data exists
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory'); sys.path.insert(0,'platform/proxmox')
from store import store_memory
store_memory('optimization', 'nova', {'finding':'missing_tags','outcome':'applied'}, tags=['proxmox','missing_tags'])
from cluster_optimizer import generate_recommendations
findings = [{'type':'missing_tags','severity':'low','detail':'test','action':'add_tags'}]
recs = generate_recommendations(findings)
has_history = any('memory_history' in r for r in recs)
print(has_history)
")
check "memory_history included in recs" "[ '$RESULT' = 'True' ]"

echo ""
echo "P77 Results: $PASS passed, $FAIL failed ($(($PASS+$FAIL)) total)"
exit $FAIL
