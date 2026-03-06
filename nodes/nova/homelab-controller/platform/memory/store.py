#!/usr/bin/env python3
"""P72 — Cluster Memory Store: durable shared memory for all cluster agents.

File-backed JSON storage. Each memory entry is a JSON file in data/memory/entries/.
An index file (data/memory/memory_index.json) tracks all entries for fast lookup.
"""
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent

# Shared memory path: prefer NFS mount, fall back to local data/
_SHARED_MEMORY = Path("/mnt/openclaw/shared_memory")
if _SHARED_MEMORY.exists() and _SHARED_MEMORY.is_dir():
    ENTRIES_DIR = _SHARED_MEMORY / "entries"
    INDEX_FILE = _SHARED_MEMORY / "memory_index.json"
    RELATIONS_DIR = _SHARED_MEMORY / "relations"
    RELATIONS_INDEX = _SHARED_MEMORY / "relations_index.json"
else:
    ENTRIES_DIR = ROOT / "data" / "memory" / "entries"
    INDEX_FILE = ROOT / "data" / "memory" / "memory_index.json"
    RELATIONS_DIR = ROOT / "data" / "memory" / "relations"
    RELATIONS_INDEX = ROOT / "data" / "memory" / "relations_index.json"

sys.path.insert(0, str(ROOT / "platform" / "events"))
from bus import emit as emit_event

VALID_CATEGORIES = [
    "incident", "investigation", "remediation", "infrastructure",
    "optimization", "policy_decision", "self_improvement",
    "operator_feedback", "routing_history",
]

VALID_STATUSES = ["active", "archived", "superseded", "invalidated"]


def _ensure_dirs():
    ENTRIES_DIR.mkdir(parents=True, exist_ok=True)


def _load_index():
    if INDEX_FILE.exists():
        with open(INDEX_FILE) as f:
            return json.load(f)
    return {"entries": [], "stats": {"total": 0, "active": 0, "archived": 0}}


def _save_index(index):
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(INDEX_FILE, "w") as f:
        json.dump(index, f, indent=2)


def _rebuild_stats(index):
    entries = index["entries"]
    index["stats"] = {
        "total": len(entries),
        "active": len([e for e in entries if e.get("status") == "active"]),
        "archived": len([e for e in entries if e.get("status") == "archived"]),
    }
    return index


def generate_memory_id():
    ts = datetime.now(timezone.utc)
    return f"MEM-{ts.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"


def store_memory(category, source_agent, payload, tags=None, related_ids=None,
                 confidence=0.5, memory_id=None):
    """Store a new memory entry. Returns the entry dict."""
    _ensure_dirs()

    if category not in VALID_CATEGORIES:
        raise ValueError(f"Invalid category: {category}. Must be one of {VALID_CATEGORIES}")

    ts = datetime.now(timezone.utc).isoformat()
    mid = memory_id or generate_memory_id()

    entry = {
        "memory_id": mid,
        "category": category,
        "created_at": ts,
        "updated_at": ts,
        "source_agent": source_agent,
        "related_ids": related_ids or [],
        "tags": tags or [],
        "confidence": max(0.0, min(1.0, confidence)),
        "status": "active",
        "payload": payload,
    }

    # Write entry file
    entry_file = ENTRIES_DIR / f"{mid}.json"
    with open(entry_file, "w") as f:
        json.dump(entry, f, indent=2)

    # Update index
    index = _load_index()
    index_entry = {
        "memory_id": mid,
        "category": category,
        "source_agent": source_agent,
        "tags": tags or [],
        "status": "active",
        "confidence": entry["confidence"],
        "created_at": ts,
        "related_ids": related_ids or [],
    }
    index["entries"].append(index_entry)
    _rebuild_stats(index)
    _save_index(index)

    emit_event("memory.entry.created", source="memory_store",
               payload={"memory_id": mid, "category": category, "agent": source_agent})
    return entry


def get_memory(memory_id):
    """Retrieve a single memory entry by ID."""
    entry_file = ENTRIES_DIR / f"{memory_id}.json"
    if entry_file.exists():
        with open(entry_file) as f:
            return json.load(f)
    return None


def update_memory(memory_id, updates):
    """Update fields on an existing memory entry."""
    entry = get_memory(memory_id)
    if not entry:
        return None

    ts = datetime.now(timezone.utc).isoformat()
    allowed_fields = ["payload", "tags", "related_ids", "confidence", "status"]
    for key in allowed_fields:
        if key in updates:
            entry[key] = updates[key]
    entry["updated_at"] = ts

    if "status" in updates and updates["status"] not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {updates['status']}")

    entry_file = ENTRIES_DIR / f"{memory_id}.json"
    with open(entry_file, "w") as f:
        json.dump(entry, f, indent=2)

    # Update index
    index = _load_index()
    for ie in index["entries"]:
        if ie["memory_id"] == memory_id:
            if "tags" in updates:
                ie["tags"] = updates["tags"]
            if "status" in updates:
                ie["status"] = updates["status"]
            if "confidence" in updates:
                ie["confidence"] = updates["confidence"]
            if "related_ids" in updates:
                ie["related_ids"] = updates["related_ids"]
            break
    _rebuild_stats(index)
    _save_index(index)

    emit_event("memory.entry.updated", source="memory_store",
               payload={"memory_id": memory_id})
    return entry


def list_memories(category=None, status="active", limit=100):
    """List memories from the index with optional filters."""
    index = _load_index()
    entries = index["entries"]
    if category:
        entries = [e for e in entries if e["category"] == category]
    if status:
        entries = [e for e in entries if e.get("status") == status]
    return entries[-limit:]


def delete_memory(memory_id):
    """Hard delete a memory entry (use update_memory with status=archived instead)."""
    entry_file = ENTRIES_DIR / f"{memory_id}.json"
    if entry_file.exists():
        os.remove(entry_file)
    index = _load_index()
    index["entries"] = [e for e in index["entries"] if e["memory_id"] != memory_id]
    _rebuild_stats(index)
    _save_index(index)
    return True


def memory_stats():
    """Return memory statistics."""
    index = _load_index()
    stats = index.get("stats", {})
    # Count by category
    cat_counts = {}
    for e in index["entries"]:
        cat = e.get("category", "unknown")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    stats["by_category"] = cat_counts
    return stats


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    if cmd == "stats":
        s = memory_stats()
        print(f"  Memory entries: {s.get('total', 0)} (active:{s.get('active', 0)} archived:{s.get('archived', 0)})")
        for cat, count in s.get("by_category", {}).items():
            print(f"    {cat}: {count}")
    elif cmd == "list":
        cat = sys.argv[2] if len(sys.argv) > 2 else None
        for e in list_memories(category=cat):
            print(f"  {e['memory_id']:<32} {e['category']:<18} {e['status']:<10} {','.join(e.get('tags', []))}")
    elif cmd == "get":
        mid = sys.argv[2] if len(sys.argv) > 2 else None
        if mid:
            entry = get_memory(mid)
            if entry:
                print(json.dumps(entry, indent=2))
            else:
                print(f"  Not found: {mid}")
    else:
        print("Usage: store.py [stats|list [category]|get <memory_id>]")


if __name__ == "__main__":
    main()
