#!/usr/bin/env python3
"""P73 — Memory Query Engine: structured query interface for cluster memory.

Provides POST /memory/query compatible query parsing and execution.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "platform" / "memory"))
from store import get_memory, list_memories
from index import search, find_similar, find_related, search_by_incident


def execute_query(query_dict):
    """Execute a structured memory query.

    Query format:
    {
        "action": "search" | "similar" | "related" | "by_incident" | "stats",
        "filters": {
            "category": "...",
            "tags": [...],
            "source_agent": "...",
            "status": "...",
            "confidence_min": 0.0,
            "related_id": "...",
            "time_after": "...",
            "time_before": "...",
            "outcome": "...",
            "node_name": "..."
        },
        "limit": 50,
        "include_payload": false
    }
    """
    action = query_dict.get("action", "search")
    filters = query_dict.get("filters", {})
    limit = query_dict.get("limit", 50)
    include_payload = query_dict.get("include_payload", False)

    if action == "search":
        results = search(
            category=filters.get("category"),
            tags=filters.get("tags"),
            source_agent=filters.get("source_agent"),
            status=filters.get("status", "active"),
            confidence_min=filters.get("confidence_min"),
            related_id=filters.get("related_id"),
            time_after=filters.get("time_after"),
            time_before=filters.get("time_before"),
            outcome=filters.get("outcome"),
            node_name=filters.get("node_name"),
            limit=limit,
        )
    elif action == "similar":
        category = filters.get("category", "incident")
        tags = filters.get("tags", [])
        exclude_id = filters.get("exclude_id")
        results = find_similar(category, tags, exclude_id=exclude_id, limit=limit)
    elif action == "related":
        memory_id = filters.get("memory_id")
        if not memory_id:
            return {"status": "error", "error": "memory_id required for related query"}
        depth = filters.get("max_depth", 2)
        results = find_related(memory_id, max_depth=depth, limit=limit)
    elif action == "by_incident":
        incident_id = filters.get("incident_id")
        if not incident_id:
            return {"status": "error", "error": "incident_id required"}
        results = search_by_incident(incident_id, limit=limit)
    elif action == "stats":
        from store import memory_stats
        return {"status": "ok", "stats": memory_stats()}
    else:
        return {"status": "error", "error": f"Unknown action: {action}"}

    # Optionally include full payloads
    if include_payload and results:
        enriched = []
        for r in results:
            mid = r.get("memory_id")
            if mid:
                full = get_memory(mid)
                if full:
                    enriched.append(full)
                else:
                    enriched.append(r)
            else:
                enriched.append(r)
        results = enriched

    return {"status": "ok", "count": len(results), "results": results}


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "query":
        # Read query from stdin or arg
        if len(sys.argv) > 2:
            query_str = sys.argv[2]
        else:
            query_str = sys.stdin.read()
        query_dict = json.loads(query_str)
        result = execute_query(query_dict)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: query.py query '<json>' | echo '<json>' | query.py query")


if __name__ == "__main__":
    main()
