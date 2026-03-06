#!/usr/bin/env python3
"""P74 — Knowledge Graph Relations: structured relationships between memory entities.

Represents relationships like caused_by, remediated_by, affects, etc.
Stored as individual relation files in data/memory/relations/.
"""
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

# Shared memory path: prefer NFS mount, fall back to local
_SHARED_MEMORY = Path("/mnt/openclaw/shared_memory")
if _SHARED_MEMORY.exists() and _SHARED_MEMORY.is_dir():
    RELATIONS_DIR = _SHARED_MEMORY / "relations"
    RELATIONS_INDEX = _SHARED_MEMORY / "relations_index.json"
else:
    RELATIONS_DIR = ROOT / "data" / "memory" / "relations"
    RELATIONS_INDEX = ROOT / "data" / "memory" / "relations_index.json"

sys.path.insert(0, str(ROOT / "platform" / "events"))
from bus import emit as emit_event

VALID_RELATION_TYPES = [
    "caused_by", "related_to", "remediated_by", "investigated_by",
    "approved_by", "superseded_by", "recurring_on", "affects",
    "optimized_by", "triggered_by", "followed_by", "blocked_by",
]

VALID_ENTITY_TYPES = [
    "incident", "node", "service", "policy", "task", "proposal",
    "investigation", "remediation", "memory", "operator", "agent",
]


def _ensure_dirs():
    RELATIONS_DIR.mkdir(parents=True, exist_ok=True)


def _load_relations_index():
    if RELATIONS_INDEX.exists():
        with open(RELATIONS_INDEX) as f:
            return json.load(f)
    return {"relations": []}


def _save_relations_index(index):
    RELATIONS_INDEX.parent.mkdir(parents=True, exist_ok=True)
    with open(RELATIONS_INDEX, "w") as f:
        json.dump(index, f, indent=2)


def add_relation(source_id, source_type, relation_type, target_id, target_type,
                 metadata=None, source_agent="system"):
    """Create a directional relation between two entities."""
    _ensure_dirs()

    if relation_type not in VALID_RELATION_TYPES:
        raise ValueError(f"Invalid relation_type: {relation_type}")

    ts = datetime.now(timezone.utc).isoformat()
    rel_id = f"REL-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

    relation = {
        "relation_id": rel_id,
        "source_id": source_id,
        "source_type": source_type,
        "relation_type": relation_type,
        "target_id": target_id,
        "target_type": target_type,
        "created_at": ts,
        "source_agent": source_agent,
        "metadata": metadata or {},
    }

    # Write relation file
    rel_file = RELATIONS_DIR / f"{rel_id}.json"
    with open(rel_file, "w") as f:
        json.dump(relation, f, indent=2)

    # Update index
    index = _load_relations_index()
    index["relations"].append({
        "relation_id": rel_id,
        "source_id": source_id,
        "source_type": source_type,
        "relation_type": relation_type,
        "target_id": target_id,
        "target_type": target_type,
        "created_at": ts,
    })
    _save_relations_index(index)

    emit_event("memory.relation.created", source="knowledge_graph",
               payload={"relation_id": rel_id, "type": relation_type,
                        "source": source_id, "target": target_id})
    return relation


def get_relation(relation_id):
    """Get a single relation by ID."""
    rel_file = RELATIONS_DIR / f"{relation_id}.json"
    if rel_file.exists():
        with open(rel_file) as f:
            return json.load(f)
    return None


def find_relations(entity_id=None, relation_type=None, direction="both", limit=50):
    """Find relations involving an entity.

    direction: "outgoing" (entity is source), "incoming" (entity is target), "both"
    """
    index = _load_relations_index()
    results = index["relations"]

    if entity_id:
        if direction == "outgoing":
            results = [r for r in results if r["source_id"] == entity_id]
        elif direction == "incoming":
            results = [r for r in results if r["target_id"] == entity_id]
        else:
            results = [r for r in results
                       if r["source_id"] == entity_id or r["target_id"] == entity_id]

    if relation_type:
        results = [r for r in results if r["relation_type"] == relation_type]

    return results[-limit:]


def get_entity_graph(entity_id, max_depth=2, limit=50):
    """Build a subgraph around an entity (BFS traversal).

    Returns nodes and edges for the local neighborhood.
    """
    visited_nodes = set()
    visited_edges = set()
    queue = [(entity_id, 0)]
    nodes = []
    edges = []

    while queue and len(nodes) < limit:
        eid, depth = queue.pop(0)
        if eid in visited_nodes or depth > max_depth:
            continue
        visited_nodes.add(eid)
        nodes.append({"id": eid, "depth": depth})

        rels = find_relations(entity_id=eid, limit=100)
        for r in rels:
            if r["relation_id"] not in visited_edges:
                visited_edges.add(r["relation_id"])
                edges.append(r)
                # Queue neighbors
                neighbor = r["target_id"] if r["source_id"] == eid else r["source_id"]
                if neighbor not in visited_nodes and depth + 1 <= max_depth:
                    queue.append((neighbor, depth + 1))

    return {"nodes": nodes, "edges": edges}


def delete_relation(relation_id):
    """Delete a relation."""
    rel_file = RELATIONS_DIR / f"{relation_id}.json"
    if rel_file.exists():
        os.remove(rel_file)
    index = _load_relations_index()
    index["relations"] = [r for r in index["relations"] if r["relation_id"] != relation_id]
    _save_relations_index(index)
    return True


def relation_stats():
    """Return relation statistics."""
    index = _load_relations_index()
    rels = index["relations"]
    type_counts = {}
    for r in rels:
        rt = r["relation_type"]
        type_counts[rt] = type_counts.get(rt, 0) + 1
    return {"total": len(rels), "by_type": type_counts}


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "stats":
        s = relation_stats()
        print(f"  Relations: {s['total']}")
        for rt, count in s.get("by_type", {}).items():
            print(f"    {rt}: {count}")
    elif cmd == "find":
        eid = sys.argv[2] if len(sys.argv) > 2 else None
        rels = find_relations(entity_id=eid)
        for r in rels:
            print(f"  {r['source_id']} --[{r['relation_type']}]--> {r['target_id']}")
    elif cmd == "graph":
        eid = sys.argv[2] if len(sys.argv) > 2 else None
        if eid:
            g = get_entity_graph(eid)
            print(f"  Nodes: {len(g['nodes'])}, Edges: {len(g['edges'])}")
            for e in g["edges"]:
                print(f"    {e['source_id']} --[{e['relation_type']}]--> {e['target_id']}")
    else:
        print("Usage: graph.py [stats|find <entity_id>|graph <entity_id>]")


if __name__ == "__main__":
    main()
