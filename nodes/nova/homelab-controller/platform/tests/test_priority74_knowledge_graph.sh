#!/usr/bin/env bash
# P74 — Knowledge Graph Relations tests
set -uo pipefail
cd "$(dirname "$0")/../.."
PASS=0; FAIL=0
check() { if eval "$2" 2>/dev/null; then echo "  [PASS] $1"; PASS=$((PASS+1)); else echo "  [FAIL] $1"; FAIL=$((FAIL+1)); fi; return 0; }

echo "=== P74: Knowledge Graph Relations ==="

# T1: graph.py exists
check "graph.py exists" "test -f platform/memory/graph.py"

# T2: graph.py is importable
check "graph.py imports" "python3 -c 'import sys; sys.path.insert(0,\".\"); sys.path.insert(0,\"platform/memory\"); from graph import add_relation, find_relations, get_entity_graph'"

# T3: add_relation creates a relation
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from graph import add_relation
r = add_relation('INC-001', 'incident', 'caused_by', 'config_drift', 'service')
print(r['relation_id'])
")
check "add_relation returns ID" "echo '$RESULT' | grep -q 'REL-'"

# T4: find_relations finds outgoing
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from graph import add_relation, find_relations
add_relation('INC-P74', 'incident', 'affects', 'nova', 'node')
rels = find_relations(entity_id='INC-P74', direction='outgoing')
print(len(rels) > 0)
")
check "find_relations outgoing" "[ '$RESULT' = 'True' ]"

# T5: find_relations finds incoming
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from graph import add_relation, find_relations
add_relation('INC-P74-IN', 'incident', 'remediated_by', 'rollback_config', 'remediation')
rels = find_relations(entity_id='rollback_config', direction='incoming')
print(len(rels) > 0)
")
check "find_relations incoming" "[ '$RESULT' = 'True' ]"

# T6: invalid relation_type raises error
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from graph import add_relation
try:
    add_relation('a', 'incident', 'invalid_type', 'b', 'node')
    print('NO_ERROR')
except ValueError:
    print('CAUGHT')
")
check "invalid relation_type raises ValueError" "[ '$RESULT' = 'CAUGHT' ]"

# T7: get_entity_graph returns nodes and edges
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from graph import add_relation, get_entity_graph
add_relation('E-P74-G1', 'incident', 'caused_by', 'E-P74-G2', 'service')
add_relation('E-P74-G2', 'service', 'affects', 'E-P74-G3', 'node')
g = get_entity_graph('E-P74-G1', max_depth=2)
print(len(g['nodes']) >= 2 and len(g['edges']) >= 1)
")
check "get_entity_graph traverses" "[ '$RESULT' = 'True' ]"

# T8: relation_stats counts types
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from graph import relation_stats
s = relation_stats()
print(s['total'] >= 0)
")
check "relation_stats returns valid data" "[ '$RESULT' = 'True' ]"

# T9: All valid relation types accepted
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from graph import add_relation, VALID_RELATION_TYPES
for rt in VALID_RELATION_TYPES:
    add_relation(f's-{rt}', 'memory', rt, f't-{rt}', 'memory')
print('ALL_OK')
")
check "all 12 relation types accepted" "[ '$RESULT' = 'ALL_OK' ]"

# T10: delete_relation removes relation
RESULT=$(python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from graph import add_relation, delete_relation, get_relation
r = add_relation('del-src', 'memory', 'related_to', 'del-tgt', 'memory')
delete_relation(r['relation_id'])
print(get_relation(r['relation_id']) is None)
")
check "delete_relation removes relation" "[ '$RESULT' = 'True' ]"

echo ""
echo "P74 Results: $PASS passed, $FAIL failed ($(($PASS+$FAIL)) total)"
exit $FAIL
