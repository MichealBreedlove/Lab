#!/usr/bin/env python3
"""incident_state.py — State helpers for incident lifecycle.

Create, read, update incident JSON. Append timeline events.
Maintain services/openclaw/incidents/latest_incident.json pointer.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List

SCRIPT_DIR = Path(__file__).parent
ROOT_DIR = SCRIPT_DIR.parent.parent
CONFIG_DIR = ROOT_DIR / "config"
ARTIFACTS_DIR = ROOT_DIR / "artifacts" / "incidents"
LATEST_DIR = ROOT_DIR.parent.parent.parent / "services" / "openclaw" / "incidents"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def _save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def load_policy() -> dict:
    return _load_json(CONFIG_DIR / "incidents_policy.json")


def generate_incident_id() -> str:
    """Generate a short incident ID like INC-20260304-a1b2."""
    date = datetime.now().strftime("%Y%m%d")
    short = uuid.uuid4().hex[:4]
    return f"INC-{date}-{short}"


def create_incident(
    trigger: str,
    severity: str,
    title: str,
    description: str = "",
    slo_id: str = None,
    evidence_paths: List[str] = None,
    blast_radius: List[str] = None,
    spof_tags: List[str] = None,
) -> Dict[str, Any]:
    """Create a new incident and persist it."""
    incident_id = generate_incident_id()

    incident = {
        "id": incident_id,
        "status": "open",
        "severity": severity,
        "title": title,
        "description": description,
        "trigger": trigger,
        "slo_id": slo_id,
        "opened_at": _now_iso(),
        "updated_at": _now_iso(),
        "closed_at": None,
        "resolved_at": None,
        "resolution_summary": None,
        "timeline": [
            {
                "timestamp": _now_iso(),
                "event": "incident_opened",
                "detail": f"Auto-opened by trigger: {trigger}",
                "actor": "system"
            }
        ],
        "evidence_paths": evidence_paths or [],
        "blast_radius": blast_radius or [],
        "spof_tags": spof_tags or [],
        "actions_taken": [],
        "postmortem_generated": False
    }

    # Save incident file
    _save_json(ARTIFACTS_DIR / f"{incident_id}.json", incident)

    # Update latest pointer
    _save_json(LATEST_DIR / "latest_incident.json", incident)

    return incident


def load_incident(incident_id: str) -> Optional[Dict]:
    """Load an incident by ID."""
    path = ARTIFACTS_DIR / f"{incident_id}.json"
    if path.exists():
        return _load_json(path)
    return None


def update_incident(incident_id: str, updates: Dict) -> Dict:
    """Update an incident with new fields."""
    incident = load_incident(incident_id)
    if not incident:
        raise ValueError(f"Incident {incident_id} not found")

    incident.update(updates)
    incident["updated_at"] = _now_iso()

    _save_json(ARTIFACTS_DIR / f"{incident_id}.json", incident)
    _save_json(LATEST_DIR / "latest_incident.json", incident)

    return incident


def add_timeline_event(
    incident_id: str,
    event: str,
    detail: str = "",
    actor: str = "system"
) -> Dict:
    """Append a timeline event to an incident."""
    incident = load_incident(incident_id)
    if not incident:
        raise ValueError(f"Incident {incident_id} not found")

    incident["timeline"].append({
        "timestamp": _now_iso(),
        "event": event,
        "detail": detail,
        "actor": actor
    })
    incident["updated_at"] = _now_iso()

    _save_json(ARTIFACTS_DIR / f"{incident_id}.json", incident)
    _save_json(LATEST_DIR / "latest_incident.json", incident)

    return incident


def close_incident(
    incident_id: str,
    resolution_summary: str,
    actor: str = "operator"
) -> Dict:
    """Close an incident with resolution summary."""
    incident = load_incident(incident_id)
    if not incident:
        raise ValueError(f"Incident {incident_id} not found")

    incident["status"] = "resolved"
    incident["resolved_at"] = _now_iso()
    incident["closed_at"] = _now_iso()
    incident["resolution_summary"] = resolution_summary
    incident["updated_at"] = _now_iso()

    incident["timeline"].append({
        "timestamp": _now_iso(),
        "event": "incident_closed",
        "detail": resolution_summary,
        "actor": actor
    })

    _save_json(ARTIFACTS_DIR / f"{incident_id}.json", incident)
    _save_json(LATEST_DIR / "latest_incident.json", incident)

    return incident


def list_incidents(status: str = None) -> List[Dict]:
    """List all incidents, optionally filtered by status."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    incidents = []
    for f in sorted(ARTIFACTS_DIR.glob("INC-*.json"), reverse=True):
        inc = _load_json(f)
        if status and inc.get("status") != status:
            continue
        incidents.append(inc)
    return incidents


def get_active_incident() -> Optional[Dict]:
    """Get the most recent open incident."""
    open_incidents = list_incidents(status="open")
    return open_incidents[0] if open_incidents else None


def is_in_cooldown(trigger: str) -> bool:
    """Check if a trigger is in cooldown (recent incident for same trigger)."""
    policy = load_policy()
    triggers = policy.get("triggers", {}).get(trigger, {})
    # Use SEV-based cooldown from severity_levels
    severity = triggers.get("severity", "SEV2")
    levels = policy.get("severity_levels", {})
    cooldown_minutes = levels.get(severity, {}).get("cooldown_minutes", 15)

    recent = list_incidents()
    for inc in recent[:10]:
        if inc.get("trigger") == trigger:
            opened = inc.get("opened_at", "")
            try:
                opened_dt = datetime.fromisoformat(opened)
                elapsed = (datetime.now(timezone.utc) - opened_dt).total_seconds() / 60
                if elapsed < cooldown_minutes:
                    return True
            except (ValueError, TypeError):
                continue
    return False
