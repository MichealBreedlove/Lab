# Memory-Aware Routing

## Overview

The task router uses historical agent performance data from cluster memory to prefer agents that have proven track records for specific task types.

## How It Works

1. When a task arrives, the router identifies candidate agents via the static routing policy
2. Before selecting, it queries `routing_history` memory for each candidate's performance on that task type
3. Agents are re-ranked by a composite score: `success_rate * 0.7 - failure_rate * 0.3 + time_bonus`
4. The highest-scoring available agent receives the task

## Metrics Tracked

| Metric | Description |
|--------|-------------|
| `success_rate` | Fraction of tasks completed successfully |
| `failure_rate` | Fraction of tasks that failed or timed out |
| `average_completion_time` | Mean duration in seconds |
| `review_required_rate` | Fraction requiring human review |

## Fallback Behavior

- If no agent has sufficient history (`min_history=2`), static routing policy is used
- If memory system is unavailable, routing falls back to static policy silently
- Memory ranking never prevents a task from being assigned — it only reorders preferences

## Recording Outcomes

After each task completes, `record_routing_outcome()` stores:
- task_id, task_type, agent_id, outcome, duration, review_required

This creates a growing performance baseline that improves routing over time.

## Example

```
Task: audit_firewall
Candidates: [mira, orin, jasper]

Memory shows:
  mira:   12 tasks, 92% success, avg 15s
  orin:    3 tasks, 67% success, avg 45s
  jasper:  1 task (insufficient history)

Result: Route to mira (score=0.644)
```

## Safety

- Memory-aware routing is advisory — it cannot assign tasks to agents lacking the capability
- Offline agents are always excluded regardless of past performance
- The router never creates autonomous escalation loops
