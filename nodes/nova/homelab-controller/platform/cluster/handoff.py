#!/usr/bin/env python3
"""Distributed artifact handoff — enables multi-agent workflows."""
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
ARTIFACT_DIR = ROOT / "data" / "cluster" / "artifacts"

sys.path.insert(0, str(ROOT / "platform" / "events"))
from bus import emit as emit_event


def create_handoff(source_agent, target_agent, artifact_type, artifact_data,
                   workflow_id=None, step=1):
    """Create a handoff artifact for agent-to-agent communication."""
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc)
    handoff_id = f"HO-{ts.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    if not workflow_id:
        workflow_id = f"WF-{ts.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

    handoff = {
        "handoff_id": handoff_id,
        "workflow_id": workflow_id,
        "step": step,
        "source_agent": source_agent,
        "target_agent": target_agent,
        "artifact_type": artifact_type,
        "artifact_data": artifact_data,
        "created_at": ts.isoformat(),
        "consumed": False,
        "consumed_at": None,
    }

    out_file = ARTIFACT_DIR / f"{handoff_id}.json"
    with open(out_file, "w") as f:
        json.dump(handoff, f, indent=2)

    emit_event("cluster.artifact.handoff", source="handoff",
               payload={"handoff_id": handoff_id, "workflow_id": workflow_id,
                        "from": source_agent, "to": target_agent, "type": artifact_type})
    return handoff


def consume_handoff(handoff_id, agent_id):
    """Mark a handoff artifact as consumed."""
    f = ARTIFACT_DIR / f"{handoff_id}.json"
    if not f.exists():
        return None
    handoff = json.load(open(f))
    if handoff["target_agent"] != agent_id:
        return None
    handoff["consumed"] = True
    handoff["consumed_at"] = datetime.now(timezone.utc).isoformat()
    with open(f, "w") as fh:
        json.dump(handoff, fh, indent=2)
    return handoff


def get_pending_handoffs(agent_id):
    """Get unconsumed handoffs for an agent."""
    if not ARTIFACT_DIR.exists():
        return []
    handoffs = []
    for f in ARTIFACT_DIR.glob("HO-*.json"):
        h = json.load(open(f))
        if h["target_agent"] == agent_id and not h["consumed"]:
            handoffs.append(h)
    return sorted(handoffs, key=lambda x: x["created_at"])


def compose_workflow(steps):
    """Define a multi-agent workflow as a sequence of steps.

    steps: list of dicts with {agent, task_type, depends_on}
    Returns workflow definition.
    """
    ts = datetime.now(timezone.utc)
    workflow_id = f"WF-{ts.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    workflow = {
        "workflow_id": workflow_id,
        "created_at": ts.isoformat(),
        "steps": [],
    }
    for i, step in enumerate(steps):
        workflow["steps"].append({
            "step": i + 1,
            "agent": step.get("agent"),
            "task_type": step.get("task_type"),
            "depends_on": step.get("depends_on"),
        })
    return workflow


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
    if cmd == "list":
        if ARTIFACT_DIR.exists():
            for f in sorted(ARTIFACT_DIR.glob("HO-*.json")):
                h = json.load(open(f))
                status = "consumed" if h["consumed"] else "pending"
                print(f"  {h['handoff_id']:<30} {h['source_agent']}->{h['target_agent']}  {status}")
        else:
            print("  No handoffs.")
    else:
        print("Usage: handoff.py [list]")


if __name__ == "__main__":
    main()
