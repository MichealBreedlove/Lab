#!/usr/bin/env bash
# P72 — Cluster Memory Store tests
set -uo pipefail
cd "$(dirname "$0")/../.."
PASS=0; FAIL=0
check() { if eval "$2" 2>/dev/null; then echo "  [PASS] $1"; PASS=$((PASS+1)); else echo "  [FAIL] $1"; FAIL=$((FAIL+1)); fi; return 0; }

echo "=== P72: Cluster Memory Store ==="

# Setup clean test state
TEST_DIR=$(mktemp -d)
export MEMORY_TEST=1
cp -r platform/memory "$TEST_DIR/memory_mod"
mkdir -p "$TEST_DIR/data/memory/entries"

# T1: store.py exists and is valid Python
check "store.py exists" "test -f platform/memory/store.py"

# T2: store.py is importable
check "store.py imports" "python3 -c 'import sys; sys.path.insert(0,\".\"); sys.path.insert(0,\"platform/memory\"); from store import store_memory, get_memory, list_memories, memory_stats'"

# T3: Can store a memory entry
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from store import store_memory
e = store_memory('incident', 'jasper', {'summary':'test incident'}, tags=['api','nova'], confidence=0.9)
print(e['memory_id'])
")
check "store_memory returns ID" "echo '$RESULT' | grep -q 'MEM-'"

# T4: Can retrieve stored entry
RESULT=$(python3 -c "
import sys, json; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from store import store_memory, get_memory
e = store_memory('incident', 'jasper', {'summary':'retrieve test'}, tags=['test'])
got = get_memory(e['memory_id'])
print(got['category'])
")
check "get_memory retrieves entry" "[ '$RESULT' = 'incident' ]"

# T5: Valid categories enforced
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from store import store_memory
try:
    store_memory('invalid_cat', 'jasper', {})
    print('NO_ERROR')
except ValueError:
    print('CAUGHT')
")
check "invalid category raises ValueError" "[ '$RESULT' = 'CAUGHT' ]"

# T6: list_memories filters by category
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from store import store_memory, list_memories
store_memory('remediation', 'nova', {'action':'restart'}, tags=['test72'])
store_memory('incident', 'jasper', {'summary':'x'}, tags=['test72'])
rems = list_memories(category='remediation')
print(len([e for e in rems if e['category']=='remediation']) > 0)
")
check "list_memories filters by category" "[ '$RESULT' = 'True' ]"

# T7: update_memory works
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from store import store_memory, update_memory, get_memory
e = store_memory('incident', 'jasper', {'summary':'update test'})
update_memory(e['memory_id'], {'status': 'archived', 'confidence': 0.99})
got = get_memory(e['memory_id'])
print(got['status'], got['confidence'])
")
check "update_memory changes fields" "echo '$RESULT' | grep -q 'archived 0.99'"

# T8: memory_stats returns counts
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from store import memory_stats
s = memory_stats()
print(s['total'] >= 0)
")
check "memory_stats returns valid data" "[ '$RESULT' = 'True' ]"

# T9: All valid categories accepted
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from store import store_memory, VALID_CATEGORIES
for cat in VALID_CATEGORIES:
    store_memory(cat, 'test', {'t': True}, tags=['t9'])
print('ALL_OK')
")
check "all 9 categories accepted" "[ '$RESULT' = 'ALL_OK' ]"

# T10: confidence clamped to [0,1]
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from store import store_memory
e1 = store_memory('incident', 'jasper', {}, confidence=5.0)
e2 = store_memory('incident', 'jasper', {}, confidence=-1.0)
print(e1['confidence'], e2['confidence'])
")
check "confidence clamped to [0,1]" "[ '$RESULT' = '1.0 0.0' ]"

echo ""
echo "P72 Results: $PASS passed, $FAIL failed ($(($PASS+$FAIL)) total)"
exit $FAIL
