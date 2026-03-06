#!/usr/bin/env python3
"""P75 — Memory-Aware Investigation: enrich investigations with historical context.

Consults cluster memory before generating conclusions. Finds similar past incidents,
ranks prior successful remediations, and adjusts confidence based on history.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "platform" / "memory"))
from store import get_memory, store_memory
from index import search, find_similar
from graph import find_relations


def build_investigation_context(incident_type, tags, node_name=None, incident_id=None):
    """Build historical context for an investigation.

    Returns enrichment data to merge into investigation output:
    - related_cases: prior similar incidents
    - historical_success_rate: success rate of similar remediations
    - prior_recommended_actions: actions that worked before
    - memory_informed_confidence: adjusted confidence based on history
    """
    # 1. Find similar past incidents
    search_tags = list(tags) if tags else []
    if node_name and node_name not in search_tags:
        search_tags.append(node_name)
    if incident_type and incident_type not in search_tags:
        search_tags.append(incident_type)

    similar = find_similar("incident", search_tags, limit=20)
    related_cases = [s["memory_id"] for s in similar]

    # 2. Find remediations for similar incidents
    remediation_memories = search(category="remediation", tags=search_tags, status=None, limit=50)

    # 3. Calculate success rate
    total_remediations = 0
    successful_remediations = 0
    action_success = {}
    action_total = {}

    for rm in remediation_memories:
        full = get_memory(rm["memory_id"])
        if not full:
            continue
        payload = full.get("payload", {})
        outcome = payload.get("outcome", "unknown")
        action = payload.get("action") or payload.get("recommended_action", "unknown")
        total_remediations += 1

        action_total[action] = action_total.get(action, 0) + 1
        if outcome in ("success", "recovered", "resolved"):
            successful_remediations += 1
            action_success[action] = action_success.get(action, 0) + 1

    historical_success_rate = (successful_remediations / total_remediations
                                if total_remediations > 0 else None)

    # 4. Rank actions by success rate
    prior_recommended_actions = []
    for action in sorted(action_total.keys(),
                         key=lambda a: action_success.get(a, 0) / action_total.get(a, 1),
                         reverse=True):
        rate = action_success.get(action, 0) / action_total[action]
        prior_recommended_actions.append({
            "action": action,
            "success_rate": round(rate, 2),
            "total_uses": action_total[action],
        })

    # 5. Calculate memory-informed confidence
    base_confidence = 0.70
    if historical_success_rate is not None:
        if historical_success_rate > 0.8:
            base_confidence = min(0.95, base_confidence + 0.15)
        elif historical_success_rate > 0.5:
            base_confidence = base_confidence + 0.05
        elif historical_success_rate < 0.3 and total_remediations > 2:
            base_confidence = max(0.30, base_confidence - 0.15)

    # Boost if many similar cases found
    if len(related_cases) >= 3:
        base_confidence = min(0.95, base_confidence + 0.05)

    memory_informed_confidence = round(base_confidence, 2)

    # 6. Also check knowledge graph for related entities
    graph_context = []
    if incident_id:
        rels = find_relations(entity_id=incident_id, limit=10)
        for r in rels:
            graph_context.append({
                "relation": r["relation_type"],
                "source": r["source_id"],
                "target": r["target_id"],
            })

    return {
        "related_cases": related_cases[:10],
        "similar_count": len(similar),
        "historical_success_rate": historical_success_rate,
        "prior_recommended_actions": prior_recommended_actions[:5],
        "memory_informed_confidence": memory_informed_confidence,
        "total_historical_remediations": total_remediations,
        "graph_context": graph_context[:5],
    }


def record_investigation_to_memory(incident_id, incident_type, investigation_result,
                                    source_agent="jasper", tags=None):
    """Record an investigation outcome to cluster memory for future reference."""
    payload = {
        "incident_id": incident_id,
        "incident_type": incident_type,
        "summary": investigation_result.get("summary", ""),
        "recommended_action": investigation_result.get("recommended_action", ""),
        "confidence": investigation_result.get("confidence", 0.5),
        "outcome": investigation_result.get("outcome", "pending"),
    }

    all_tags = list(tags or [])
    if incident_type and incident_type not in all_tags:
        all_tags.append(incident_type)

    return store_memory(
        category="investigation",
        source_agent=source_agent,
        payload=payload,
        tags=all_tags,
        related_ids=[incident_id] if incident_id else [],
        confidence=investigation_result.get("confidence", 0.5),
    )


def record_remediation_to_memory(incident_id, action, outcome, source_agent="jasper",
                                  tags=None, confidence=0.5):
    """Record a remediation outcome to cluster memory."""
    payload = {
        "incident_id": incident_id,
        "action": action,
        "outcome": outcome,
    }
    all_tags = list(tags or [])
    return store_memory(
        category="remediation",
        source_agent=source_agent,
        payload=payload,
        tags=all_tags,
        related_ids=[incident_id] if incident_id else [],
        confidence=confidence,
    )


def main():
    if len(sys.argv) > 1:
        incident_type = sys.argv[1]
        tags = sys.argv[2].split(",") if len(sys.argv) > 2 else []
        ctx = build_investigation_context(incident_type, tags)
        print(json.dumps(ctx, indent=2))
    else:
        print("Usage: investigation_context.py <incident_type> [tag1,tag2,...]")


if __name__ == "__main__":
    main()
