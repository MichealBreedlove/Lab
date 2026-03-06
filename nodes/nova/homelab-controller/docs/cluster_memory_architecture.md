# Cluster Memory Architecture

## Overview

The cluster memory system provides durable, structured, queryable storage for all operational knowledge across the distributed agent cluster. Every agent (Jasper, Nova, Mira, Orin) reads from and writes to shared memory, enabling the cluster to learn from history.

## Components

| Component | File | Purpose |
|-----------|------|---------|
| Memory Store | `platform/memory/store.py` | CRUD operations, file-backed JSON storage |
| Memory Index | `platform/memory/index.py` | Structured search, similarity matching |
| Query Engine | `platform/memory/query.py` | POST /memory/query compatible query execution |
| Knowledge Graph | `platform/memory/graph.py` | Entity relationships (caused_by, affects, etc.) |
| Investigation Context | `platform/memory/investigation_context.py` | Historical enrichment for investigations |
| Routing History | `platform/memory/routing_history.py` | Agent performance tracking for routing |
| Lifecycle Manager | `platform/memory/lifecycle.py` | Retention, archival, rollup summaries |

## Storage Layout

```
data/memory/
├── memory_index.json          # Fast-lookup index of all entries
├── entries/                   # Individual memory entry JSON files
│   ├── MEM-20260305-220000-abc123.json
│   └── ...
├── relations/                 # Knowledge graph relation files
│   ├── REL-20260305-220100-def456.json
│   └── ...
└── relations_index.json       # Fast-lookup index of relations
```

## Memory Entry Schema

```json
{
  "memory_id": "MEM-YYYYMMDD-HHMMSS-xxxxxx",
  "category": "incident|investigation|remediation|infrastructure|optimization|policy_decision|self_improvement|operator_feedback|routing_history",
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "source_agent": "jasper|nova|mira|orin|system|api",
  "related_ids": ["INC-...", "TASK-..."],
  "tags": ["api", "nova", "config_drift"],
  "confidence": 0.0-1.0,
  "status": "active|archived|superseded|invalidated",
  "payload": { ... }
}
```

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/memory` | List entries (optional `?category=` filter) |
| GET | `/memory/stats` | Memory + relation + hygiene statistics |
| POST | `/memory` | Store a new memory entry |
| POST | `/memory/query` | Execute structured query |
| POST | `/memory/relation` | Create a knowledge graph relation |

## Safety Constraints

- Memory **informs** decisions but **never bypasses** policy
- Memory cannot override approval requirements
- Memory cannot reclassify high-risk actions as low-risk
- `policy_decision` and `operator_feedback` entries are never auto-deleted
- All memory writes emit events to the event bus for auditability
