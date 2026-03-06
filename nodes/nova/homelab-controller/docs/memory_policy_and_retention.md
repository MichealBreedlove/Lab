# Memory Policy and Retention

## Overview

The memory lifecycle system prevents unbounded growth, staleness, and noise in the cluster memory store. It enforces category-based retention, archives old entries, and rolls up repeated patterns into summaries.

## Policy File

`config/memory_policy.json` controls all retention behavior:

```json
{
  "enabled": true,
  "archive_after_days": {
    "routing_history": 30,
    "optimization": 60,
    "incident": 365,
    "investigation": 365,
    "remediation": 365,
    "infrastructure": 180,
    "operator_feedback": 365,
    "policy_decision": 365,
    "self_improvement": 180
  },
  "never_auto_delete": ["policy_decision", "operator_feedback"],
  "summary_rollups": {
    "routing_history": true,
    "optimization": true
  }
}
```

## Retention Rules

| Category | Archive After | Auto-Delete? |
|----------|--------------|--------------|
| routing_history | 30 days | Yes |
| optimization | 60 days | Yes |
| infrastructure | 180 days | Yes |
| self_improvement | 180 days | Yes |
| incident | 365 days | Yes |
| investigation | 365 days | Yes |
| remediation | 365 days | Yes |
| operator_feedback | 365 days | **Never** |
| policy_decision | 365 days | **Never** |

## Archive vs Delete

- **Archive**: Status changed to `archived`. Entry file remains. Not returned in default searches (which filter `status=active`).
- **Delete**: Hard removal. Only used via explicit `delete_memory()` call. Never automated for protected categories.

## Summary Rollups

For high-volume categories (`routing_history`, `optimization`), the lifecycle manager can generate rollup summaries:

1. Groups entries by common tag sets
2. Creates a single summary entry with aggregate statistics
3. Archives the original entries
4. Summary entry tagged with `rollup_summary`

This prevents routing history from growing unboundedly while preserving the aggregate knowledge.

## Hygiene Report

`memory_hygiene_report()` returns:
- Total entries (active + archived)
- Stale candidates (entries past retention threshold but not yet archived)
- Category distribution
- Policy status

## Lifecycle Tick

`lifecycle_tick()` runs one maintenance cycle:
1. Archives stale entries per retention policy
2. Generates rollup summaries for enabled categories
3. Returns hygiene report

Recommended: run daily via `oc memory tick` or scheduled task.
