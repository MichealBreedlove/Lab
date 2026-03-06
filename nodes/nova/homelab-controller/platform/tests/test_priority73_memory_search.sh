#!/usr/bin/env bash
# P73 — Memory Index and Search tests
set -euo pipefail
cd "$(dirname "$0")/../.."
PASS=0; FAIL=0
check() { if eval "$2"; then echo "  [PASS] $1"; ((PASS++)); else echo "  [FAIL] $1"; ((FAIL++)); fi; }

echo "=== P73: Memory Index and Search ==="

# T1: index.py exists
check "index.py exists" "test -f platform/memory/index.py"

# T2: query.py exists
check "query.py exists" "test -f platform/memory/query.py"

# T3: search by category
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from store import store_memory
from index import search
store_memory('incident', 'jasper', {'summary':'p73 test'}, tags=['p73','api'])
results = search(category='incident', tags=['p73'])
print(len(results) > 0)
")
check "search by category+tag returns results" "[ '$RESULT' = 'True' ]"

# T4: search by source_agent
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from store import store_memory
from index import search
store_memory('remediation', 'orin', {'action':'analyze'}, tags=['p73_agent'])
results = search(source_agent='orin', tags=['p73_agent'])
print(len(results) > 0)
")
check "search by source_agent" "[ '$RESULT' = 'True' ]"

# T5: search by confidence_min
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from store import store_memory
from index import search
store_memory('incident', 'jasper', {'s':'high conf'}, tags=['p73_conf'], confidence=0.95)
store_memory('incident', 'jasper', {'s':'low conf'}, tags=['p73_conf'], confidence=0.30)
results = search(tags=['p73_conf'], confidence_min=0.90)
print(all(r['confidence'] >= 0.90 for r in results))
")
check "search by confidence_min filters correctly" "[ '$RESULT' = 'True' ]"

# T6: find_similar returns ranked results
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from store import store_memory
from index import find_similar
store_memory('incident', 'jasper', {}, tags=['api_down','nova','config_drift'])
store_memory('incident', 'jasper', {}, tags=['api_down','nova'])
results = find_similar('incident', ['api_down','nova','config_drift'])
print(len(results) > 0)
")
check "find_similar returns ranked results" "[ '$RESULT' = 'True' ]"

# T7: find_related traverses links
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from store import store_memory
from index import find_related
e1 = store_memory('incident', 'jasper', {}, tags=['p73_rel'])
e2 = store_memory('remediation', 'jasper', {}, tags=['p73_rel'], related_ids=[e1['memory_id']])
related = find_related(e1['memory_id'])
print(len(related) > 0)
")
check "find_related traverses links" "[ '$RESULT' = 'True' ]"

# T8: query engine search action
RESULT=$(python3 -c "
import sys, json; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from query import execute_query
result = execute_query({'action':'search','filters':{'category':'incident'}})
print(result['status'])
")
check "query engine search action returns ok" "[ '$RESULT' = 'ok' ]"

# T9: query engine stats action
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from query import execute_query
result = execute_query({'action':'stats'})
print('total' in result.get('stats', {}))
")
check "query engine stats returns total" "[ '$RESULT' = 'True' ]"

# T10: search_by_incident
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from store import store_memory
from index import search_by_incident
store_memory('investigation', 'orin', {'s':'inv'}, tags=['INC-TEST-73'], related_ids=['INC-TEST-73'])
results = search_by_incident('INC-TEST-73')
print(len(results) > 0)
")
check "search_by_incident finds related entries" "[ '$RESULT' = 'True' ]"

echo ""
echo "P73 Results: $PASS passed, $FAIL failed ($(($PASS+$FAIL)) total)"
exit $FAIL
