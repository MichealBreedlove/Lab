#!/usr/bin/env python3
"""P78 — Memory Retention, Hygiene, and Lifecycle Policy.

Prevents memory from becoming noisy, stale, or unsafe.
Archives old entries per category-based retention, summarizes repeated entries,
and enforces policy constraints on deletion.
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
POLICY_FILE = ROOT / "config" / "memory_policy.json"

sys.path.insert(0, str(ROOT / "platform" / "memory"))
sys.path.insert(0, str(ROOT / "platform" / "events"))
from store import _load_index, _save_index, _rebuild_stats, get_memory, update_memory, \
    store_memory, list_memories, ENTRIES_DIR
from bus import emit as emit_event


def load_policy():
    """Load memory retention policy."""
    if POLICY_FILE.exists():
        with open(POLICY_FILE) as f:
            return json.load(f)
    return {
        "enabled": True,
        "archive_after_days": {
            "routing_history": 30,
            "optimization": 60,
            "incident": 365,
            "investigation": 365,
            "remediation": 365,
            "infrastructure": 180,
            "operator_feedback": 365,
            "policy_decision": 365,
            "self_improvement": 180,
        },
        "never_auto_delete": ["policy_decision", "operator_feedback"],
        "summary_rollups": {
            "routing_history": True,
            "optimization": True,
        },
    }


def archive_stale_entries(dry_run=False):
    """Archive entries that exceed their category retention threshold."""
    policy = load_policy()
    if not policy.get("enabled", True):
        return {"archived": 0, "skipped": 0, "message": "Policy disabled"}

    archive_days = policy.get("archive_after_days", {})
    never_delete = set(policy.get("never_auto_delete", []))
    now = datetime.now(timezone.utc)
    archived = 0
    skipped = 0

    index = _load_index()
    for ie in index["entries"]:
        if ie.get("status") != "active":
            continue

        category = ie.get("category", "unknown")
        max_days = archive_days.get(category, 365)
        created = ie.get("created_at", "")

        try:
            created_dt = datetime.fromisoformat(created)
        except (ValueError, TypeError):
            continue

        age_days = (now - created_dt).days

        if age_days > max_days:
            if category in never_delete:
                skipped += 1
                continue
            if not dry_run:
                update_memory(ie["memory_id"], {"status": "archived"})
            archived += 1

    result = {"archived": archived, "skipped": skipped, "dry_run": dry_run}
    if not dry_run and archived > 0:
        emit_event("memory.lifecycle.archive", source="lifecycle",
                   payload=result)
    return result


def generate_rollup_summary(category, min_entries=5):
    """Generate a summary rollup for a category with many similar entries.

    Creates a new summary memory entry and archives the originals.
    """
    policy = load_policy()
    rollup_categories = policy.get("summary_rollups", {})
    if not rollup_categories.get(category, False):
        return {"status": "skipped", "reason": f"Rollup not enabled for {category}"}

    entries = list_memories(category=category, status="active", limit=500)
    if len(entries) < min_entries:
        return {"status": "skipped", "reason": f"Only {len(entries)} entries, need {min_entries}"}

    # Group by common tags
    tag_groups = {}
    for ie in entries:
        key = ",".join(sorted(ie.get("tags", [])))
        if key not in tag_groups:
            tag_groups[key] = []
        tag_groups[key].append(ie)

    rollups_created = 0
    for tag_key, group in tag_groups.items():
        if len(group) < min_entries:
            continue

        # Build summary
        tags = group[0].get("tags", [])
        total = len(group)
        avg_confidence = sum(e.get("confidence", 0.5) for e in group) / total

        summary_payload = {
            "type": "rollup_summary",
            "category": category,
            "entry_count": total,
            "date_range": {
                "first": group[0].get("created_at", ""),
                "last": group[-1].get("created_at", ""),
            },
            "average_confidence": round(avg_confidence, 3),
            "common_tags": tags,
            "original_ids": [e["memory_id"] for e in group],
        }

        # Create summary entry
        store_memory(
            category=category,
            source_agent="lifecycle",
            payload=summary_payload,
            tags=tags + ["rollup_summary"],
            confidence=avg_confidence,
        )

        # Archive originals
        for e in group:
            update_memory(e["memory_id"], {"status": "archived"})

        rollups_created += 1

    result = {"status": "ok", "rollups_created": rollups_created, "category": category}
    if rollups_created > 0:
        emit_event("memory.lifecycle.rollup", source="lifecycle", payload=result)
    return result


def memory_hygiene_report():
    """Generate a hygiene report on memory state."""
    index = _load_index()
    entries = index["entries"]

    total = len(entries)
    active = len([e for e in entries if e.get("status") == "active"])
    archived = len([e for e in entries if e.get("status") == "archived"])

    now = datetime.now(timezone.utc)
    policy = load_policy()
    archive_days = policy.get("archive_after_days", {})

    stale_candidates = 0
    for e in entries:
        if e.get("status") != "active":
            continue
        category = e.get("category", "unknown")
        max_days = archive_days.get(category, 365)
        created = e.get("created_at", "")
        try:
            created_dt = datetime.fromisoformat(created)
            if (now - created_dt).days > max_days:
                stale_candidates += 1
        except (ValueError, TypeError):
            pass

    # Category distribution
    cat_counts = {}
    for e in entries:
        cat = e.get("category", "unknown")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    return {
        "total_entries": total,
        "active": active,
        "archived": archived,
        "stale_candidates": stale_candidates,
        "by_category": cat_counts,
        "policy_enabled": policy.get("enabled", True),
    }


def lifecycle_tick(dry_run=False):
    """Run one lifecycle maintenance cycle."""
    archive_result = archive_stale_entries(dry_run=dry_run)

    # Run rollups for enabled categories
    policy = load_policy()
    rollup_results = []
    for category, enabled in policy.get("summary_rollups", {}).items():
        if enabled:
            result = generate_rollup_summary(category)
            rollup_results.append(result)

    return {
        "archive": archive_result,
        "rollups": rollup_results,
        "hygiene": memory_hygiene_report(),
    }


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    if cmd == "report":
        r = memory_hygiene_report()
        print(f"  Memory: {r['total_entries']} total ({r['active']} active, {r['archived']} archived)")
        print(f"  Stale candidates: {r['stale_candidates']}")
        for cat, count in r.get("by_category", {}).items():
            print(f"    {cat}: {count}")
    elif cmd == "archive":
        dry = "--dry-run" in sys.argv
        result = archive_stale_entries(dry_run=dry)
        print(f"  Archived: {result['archived']}, Skipped: {result['skipped']}")
    elif cmd == "tick":
        dry = "--dry-run" in sys.argv
        result = lifecycle_tick(dry_run=dry)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: lifecycle.py [report|archive [--dry-run]|tick [--dry-run]]")


if __name__ == "__main__":
    main()
