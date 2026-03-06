#!/usr/bin/env python3
"""P73 — Memory Index: efficient search across memory entries.

Provides structured filtering, tag search, time-range queries, and
related-case discovery for the cluster memory system.
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "platform" / "memory"))
from store import _load_index, get_memory, ENTRIES_DIR


def search(category=None, tags=None, source_agent=None, status="active",
           confidence_min=None, related_id=None, time_after=None, time_before=None,
           outcome=None, node_name=None, limit=50):
    """Search memory entries with structured filters.

    Returns list of index entries (lightweight). Use get_memory() for full payload.
    """
    index = _load_index()
    results = index["entries"]

    if category:
        results = [e for e in results if e["category"] == category]
    if status:
        results = [e for e in results if e.get("status") == status]
    if source_agent:
        results = [e for e in results if e.get("source_agent") == source_agent]
    if confidence_min is not None:
        results = [e for e in results if e.get("confidence", 0) >= confidence_min]
    if tags:
        tag_set = set(tags) if isinstance(tags, list) else {tags}
        results = [e for e in results if tag_set.intersection(set(e.get("tags", [])))]
    if related_id:
        results = [e for e in results if related_id in e.get("related_ids", [])]
    if time_after:
        results = [e for e in results if e.get("created_at", "") >= time_after]
    if time_before:
        results = [e for e in results if e.get("created_at", "") <= time_before]

    # Deep filters require loading full entries
    if outcome or node_name:
        filtered = []
        for ie in results:
            full = get_memory(ie["memory_id"])
            if not full:
                continue
            payload = full.get("payload", {})
            if outcome and payload.get("outcome") != outcome:
                continue
            if node_name and node_name not in full.get("tags", []) and \
               node_name != payload.get("node") and node_name != payload.get("target_node"):
                continue
            filtered.append(ie)
        results = filtered

    return results[-limit:]


def find_related(memory_id, max_depth=2, limit=20):
    """Find memories related to a given memory_id via related_ids links.

    Performs breadth-first traversal up to max_depth hops.
    """
    visited = set()
    queue = [(memory_id, 0)]
    related = []

    while queue:
        mid, depth = queue.pop(0)
        if mid in visited or depth > max_depth:
            continue
        visited.add(mid)

        entry = get_memory(mid)
        if not entry:
            continue
        if mid != memory_id:
            related.append({"memory_id": mid, "depth": depth, "category": entry.get("category")})

        if depth < max_depth:
            for rid in entry.get("related_ids", []):
                if rid not in visited:
                    queue.append((rid, depth + 1))

            # Also find entries that reference this memory
            index = _load_index()
            for ie in index["entries"]:
                if mid in ie.get("related_ids", []) and ie["memory_id"] not in visited:
                    queue.append((ie["memory_id"], depth + 1))

    return related[:limit]


def find_similar(category, tags, exclude_id=None, limit=10):
    """Find similar memories by category and tag overlap.

    Ranks by number of matching tags (Jaccard-like).
    """
    index = _load_index()
    tag_set = set(tags) if isinstance(tags, list) else {tags}
    candidates = []

    for ie in index["entries"]:
        if ie.get("status") != "active":
            continue
        if exclude_id and ie["memory_id"] == exclude_id:
            continue
        if ie.get("category") != category:
            continue
        entry_tags = set(ie.get("tags", []))
        overlap = len(tag_set.intersection(entry_tags))
        if overlap > 0:
            union = len(tag_set.union(entry_tags))
            score = overlap / union if union > 0 else 0
            candidates.append({"memory_id": ie["memory_id"], "score": score,
                               "overlap_tags": list(tag_set.intersection(entry_tags)),
                               "confidence": ie.get("confidence", 0)})

    candidates.sort(key=lambda x: (x["score"], x["confidence"]), reverse=True)
    return candidates[:limit]


def search_by_incident(incident_id, limit=20):
    """Find all memories related to a specific incident."""
    results = search(related_id=incident_id, status=None, limit=limit)
    # Also search tags
    tag_results = search(tags=[incident_id], status=None, limit=limit)
    seen = {r["memory_id"] for r in results}
    for tr in tag_results:
        if tr["memory_id"] not in seen:
            results.append(tr)
    return results[:limit]


def search_by_task(task_id, limit=20):
    """Find all memories related to a specific task."""
    return search(related_id=task_id, status=None, limit=limit)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "search":
        cat = None
        tags = None
        agent = None
        args = sys.argv[2:]
        i = 0
        while i < len(args):
            if args[i] == "--category" and i + 1 < len(args):
                cat = args[i + 1]; i += 2
            elif args[i] == "--tag" and i + 1 < len(args):
                tags = [args[i + 1]]; i += 2
            elif args[i] == "--agent" and i + 1 < len(args):
                agent = args[i + 1]; i += 2
            else:
                i += 1
        results = search(category=cat, tags=tags, source_agent=agent)
        for r in results:
            print(f"  {r['memory_id']:<32} {r['category']:<18} {','.join(r.get('tags', []))}")
    elif cmd == "similar":
        cat = sys.argv[2] if len(sys.argv) > 2 else "incident"
        tags = sys.argv[3].split(",") if len(sys.argv) > 3 else []
        results = find_similar(cat, tags)
        for r in results:
            print(f"  {r['memory_id']:<32} score={r['score']:.2f} tags={r['overlap_tags']}")
    else:
        print("Usage: index.py [search --category X --tag Y --agent Z | similar <cat> <tag1,tag2>]")


if __name__ == "__main__":
    main()
