#!/usr/bin/env python3
"""P76 — Memory-Aware Routing: track and use agent performance history for task routing.

Records routing outcomes to memory and provides performance metrics
that the router can use to prefer better-performing agents.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "platform" / "memory"))
from store import store_memory, list_memories, get_memory
from index import search


def record_routing_outcome(task_id, task_type, agent_id, outcome, duration_seconds=None,
                           required_review=False):
    """Record a task routing outcome to memory."""
    payload = {
        "task_id": task_id,
        "task_type": task_type,
        "agent_id": agent_id,
        "outcome": outcome,  # success, failed, timed_out, review_required
        "duration_seconds": duration_seconds,
        "required_review": required_review,
    }
    return store_memory(
        category="routing_history",
        source_agent="jasper",
        payload=payload,
        tags=[task_type, agent_id, outcome],
        related_ids=[task_id],
        confidence=1.0,  # Factual record
    )


def get_agent_performance(agent_id, task_type=None, limit=100):
    """Get performance metrics for an agent, optionally filtered by task type.

    Returns:
    {
        "success_rate": float,
        "average_completion_time": float or None,
        "failure_rate": float,
        "review_required_rate": float,
        "total_tasks": int,
        "task_type_breakdown": {...}
    }
    """
    tags = [agent_id]
    if task_type:
        tags.append(task_type)

    entries = search(category="routing_history", tags=tags, status=None, limit=limit)

    total = 0
    successes = 0
    failures = 0
    timeouts = 0
    reviews = 0
    durations = []
    type_breakdown = {}

    for ie in entries:
        full = get_memory(ie["memory_id"])
        if not full:
            continue
        p = full.get("payload", {})
        if p.get("agent_id") != agent_id:
            continue
        if task_type and p.get("task_type") != task_type:
            continue

        total += 1
        outcome = p.get("outcome", "unknown")
        tt = p.get("task_type", "unknown")

        if outcome == "success":
            successes += 1
        elif outcome == "failed":
            failures += 1
        elif outcome == "timed_out":
            timeouts += 1
        if p.get("required_review"):
            reviews += 1
        if p.get("duration_seconds") is not None:
            durations.append(p["duration_seconds"])

        if tt not in type_breakdown:
            type_breakdown[tt] = {"total": 0, "success": 0, "failed": 0}
        type_breakdown[tt]["total"] += 1
        if outcome == "success":
            type_breakdown[tt]["success"] += 1
        elif outcome in ("failed", "timed_out"):
            type_breakdown[tt]["failed"] += 1

    return {
        "agent_id": agent_id,
        "task_type_filter": task_type,
        "total_tasks": total,
        "success_rate": round(successes / total, 3) if total > 0 else None,
        "failure_rate": round((failures + timeouts) / total, 3) if total > 0 else None,
        "review_required_rate": round(reviews / total, 3) if total > 0 else None,
        "average_completion_time": round(sum(durations) / len(durations), 1) if durations else None,
        "task_type_breakdown": type_breakdown,
    }


def get_best_agent_for_task(task_type, candidate_agents, min_history=2):
    """Rank candidate agents by historical performance for a task type.

    Returns sorted list of (agent_id, score, metrics).
    """
    rankings = []
    for agent_id in candidate_agents:
        perf = get_agent_performance(agent_id, task_type=task_type)
        total = perf["total_tasks"]

        if total < min_history:
            # Not enough data — neutral score
            rankings.append((agent_id, 0.5, perf))
            continue

        sr = perf["success_rate"] or 0
        fr = perf["failure_rate"] or 0
        avg_time = perf["average_completion_time"]

        # Score: weighted success rate - failure penalty
        score = sr * 0.7 - fr * 0.3
        # Time bonus: faster agents get slight boost (capped)
        if avg_time is not None and avg_time > 0:
            time_bonus = max(0, min(0.1, 1.0 / avg_time * 10))
            score += time_bonus

        rankings.append((agent_id, round(score, 3), perf))

    rankings.sort(key=lambda x: x[1], reverse=True)
    return rankings


def get_all_agent_performance_summary():
    """Get performance summary for all agents."""
    entries = search(category="routing_history", status=None, limit=500)

    agents = set()
    for ie in entries:
        for tag in ie.get("tags", []):
            if tag in ("jasper", "nova", "mira", "orin"):
                agents.add(tag)

    summaries = {}
    for agent_id in agents:
        summaries[agent_id] = get_agent_performance(agent_id)

    return summaries


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "summary"
    if cmd == "summary":
        s = get_all_agent_performance_summary()
        for agent_id, perf in s.items():
            sr = perf["success_rate"]
            sr_str = f"{sr:.1%}" if sr is not None else "N/A"
            print(f"  {agent_id:<10} tasks={perf['total_tasks']} success={sr_str}")
    elif cmd == "agent":
        aid = sys.argv[2] if len(sys.argv) > 2 else "jasper"
        perf = get_agent_performance(aid)
        print(json.dumps(perf, indent=2))
    elif cmd == "rank":
        task_type = sys.argv[2] if len(sys.argv) > 2 else "audit_firewall"
        candidates = sys.argv[3].split(",") if len(sys.argv) > 3 else ["jasper", "nova", "mira", "orin"]
        rankings = get_best_agent_for_task(task_type, candidates)
        for agent_id, score, perf in rankings:
            print(f"  {agent_id:<10} score={score:.3f} tasks={perf['total_tasks']}")
    else:
        print("Usage: routing_history.py [summary|agent <id>|rank <task_type> <agent1,agent2>]")


if __name__ == "__main__":
    main()
