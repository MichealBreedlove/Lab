# Distributed Memory Demo Scenarios

## Scenario 1: API Incident with Historical Context

**Setup:** Seed 5 prior API outage remediation memories (4 success with `rollback_config`, 1 failure with `restart_service`).

**Trigger:** New `api_down` incident on Nova.

**Expected:**
1. Investigator calls `build_investigation_context("api_down", ["api", "nova"])`
2. Returns 5 related cases, `historical_success_rate` ≈ 0.80
3. `prior_recommended_actions` ranks `rollback_config` first (100% success vs 0%)
4. `memory_informed_confidence` elevated to ~0.85
5. Investigation recommends `rollback_config` with high confidence
6. Investigation and remediation outcome recorded to memory for future reference

**Demo command:**
```bash
python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from store import store_memory
from investigation_context import build_investigation_context
for i in range(4):
    store_memory('remediation', 'jasper', {'action':'rollback_config','outcome':'success'}, tags=['api_down','nova'])
store_memory('remediation', 'jasper', {'action':'restart_service','outcome':'failed'}, tags=['api_down','nova'])
ctx = build_investigation_context('api_down', ['api_down','nova'])
import json; print(json.dumps(ctx, indent=2))
"
```

---

## Scenario 2: Firewall Optimization with Rejection History

**Setup:** Seed 3 rejected `duplicate_alias` cleanup recommendations.

**Trigger:** Mira runs firewall audit and finds duplicate aliases again.

**Expected:**
1. `generate_recommendations()` queries memory for `duplicate_alias` history
2. Finds 3 prior rejections, 0 acceptances
3. Recommendation suppressed: `action = "suppressed_by_memory"`
4. Operator not nagged with same recommendation they've declined 3 times

**Demo command:**
```bash
python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory'); sys.path.insert(0,'platform/network')
from store import store_memory
for i in range(3):
    store_memory('optimization', 'mira', {'finding':'duplicate_alias','outcome':'rejected'}, tags=['firewall','duplicate_alias'])
from firewall_optimizer import generate_recommendations
findings = [{'type':'duplicate_alias','severity':'low','detail':'Alias A = Alias B','category':'aliases'}]
import json; print(json.dumps(generate_recommendations(findings), indent=2))
"
```

---

## Scenario 3: Memory-Aware Task Routing

**Setup:** Seed routing history — Mira: 10 successful firewall audits, Orin: 2 failed firewall audits.

**Trigger:** New `audit_firewall` task needs routing.

**Expected:**
1. Router queries `get_best_agent_for_task("audit_firewall", ["mira", "orin"])`
2. Mira scores higher (100% success vs 0%)
3. Task routed to Mira with reason `"Memory-ranked"`

**Demo command:**
```bash
python3 -c "
import sys; sys.path.insert(0,'.'); sys.path.insert(0,'platform/memory')
from routing_history import record_routing_outcome, get_best_agent_for_task
for i in range(10):
    record_routing_outcome(f'TASK-DEMO-{i}', 'audit_firewall', 'mira', 'success', duration_seconds=15)
for i in range(2):
    record_routing_outcome(f'TASK-DEMO-F{i}', 'audit_firewall', 'orin', 'failed')
rankings = get_best_agent_for_task('audit_firewall', ['mira','orin'], min_history=1)
for agent, score, perf in rankings:
    print(f'{agent}: score={score:.3f} success_rate={perf[\"success_rate\"]}')
"
```

---

## Scenario 4: Knowledge Graph Traversal

**Setup:** Create incident → caused_by → config_drift → affects → nova chain.

**Trigger:** Query graph for `api_down` entity.

**Expected:**
1. `get_entity_graph("api_down", max_depth=2)` returns 3+ nodes, 2+ edges
2. Full causal chain visible: incident → drift → node

---

## Scenario 5: Memory Lifecycle Hygiene

**Setup:** Create 100 `routing_history` entries with old timestamps.

**Trigger:** `lifecycle_tick()`

**Expected:**
1. Stale entries archived per 30-day policy
2. Rollup summary created for the group
3. Hygiene report shows reduced active count
