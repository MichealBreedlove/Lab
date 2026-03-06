# Knowledge Graph Model

## Overview

The knowledge graph represents directional relationships between entities in the cluster. It enables agents to reason across history — tracing an incident back to its root cause, finding which remediation fixed it, and who approved it.

## Relation Types

| Type | Description | Example |
|------|-------------|---------|
| `caused_by` | Root cause link | incident → config_drift |
| `related_to` | General association | incident A → incident B |
| `remediated_by` | Fix applied | incident → rollback_config |
| `investigated_by` | Who analyzed | incident → orin |
| `approved_by` | Operator approval | proposal → operator |
| `superseded_by` | Replaced by newer | old_fix → new_fix |
| `recurring_on` | Repeated pattern | incident → node |
| `affects` | Impact link | incident → nova |
| `optimized_by` | Improvement applied | service → optimization |
| `triggered_by` | Cause chain | alert → incident |
| `followed_by` | Sequence | step_1 → step_2 |
| `blocked_by` | Dependency | task → approval |

## Entity Types

`incident`, `node`, `service`, `policy`, `task`, `proposal`, `investigation`, `remediation`, `memory`, `operator`, `agent`

## Relation Schema

```json
{
  "relation_id": "REL-YYYYMMDD-HHMMSS-xxxxxx",
  "source_id": "INC-001",
  "source_type": "incident",
  "relation_type": "caused_by",
  "target_id": "config_drift",
  "target_type": "service",
  "created_at": "ISO-8601",
  "source_agent": "jasper",
  "metadata": {}
}
```

## Graph Traversal

`get_entity_graph(entity_id, max_depth=2)` performs BFS from any entity, returning the local neighborhood of nodes and edges. This powers:

- Investigation context: "What else was affected by this incident?"
- Remediation lookup: "What fixed similar issues before?"
- Impact analysis: "Which nodes does this service affect?"

## Example Graph

```
incident:api_down
  ├── caused_by → service:config_drift
  ├── affects → node:nova
  ├── investigated_by → agent:orin
  ├── remediated_by → remediation:rollback_config
  │   └── approved_by → operator:micheal
  └── related_to → incident:prior_api_down
```
