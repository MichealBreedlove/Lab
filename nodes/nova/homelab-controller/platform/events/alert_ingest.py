#!/usr/bin/env python3
"""Alertmanager webhook ingestion — converts Prometheus alerts into platform events/incidents."""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
INCIDENTS_FILE = ROOT / "artifacts" / "recovery" / "incidents.json"

from bus import emit as emit_event

# Map alertname to incident type
ALERT_TYPE_MAP = {
    "API_Down": "api_down",
    "APIDown": "api_down",
    "api_down": "api_down",
    "Node_Unreachable": "node_unreachable",
    "NodeUnreachable": "node_unreachable",
    "node_unreachable": "node_unreachable",
    "Config_Drift": "config_drift",
    "ConfigDrift": "config_drift",
    "config_drift": "config_drift",
    "HighCPU": "high_cpu",
    "HighMemory": "high_memory",
    "DiskPressure": "disk_pressure",
}


def load_incidents():
    """Load existing incidents."""
    INCIDENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if INCIDENTS_FILE.exists():
        with open(INCIDENTS_FILE) as f:
            return json.load(f)
    return {"incidents": []}


def save_incidents(data):
    """Save incidents."""
    with open(INCIDENTS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def find_active_incident(incidents_data, alertname, instance):
    """Find an active incident matching alertname+instance for deduplication."""
    for inc in incidents_data.get("incidents", []):
        if (inc.get("status") in ("open", "investigating") and
                inc.get("alertname") == alertname and
                inc.get("instance") == instance):
            return inc
    return None


def create_incident(alertname, instance, severity, description, starts_at):
    """Create a new incident from an alert."""
    ts = datetime.now(timezone.utc)
    inc_id = f"INC-{ts.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    inc_type = ALERT_TYPE_MAP.get(alertname, alertname.lower().replace(" ", "_"))

    incident = {
        "incident_id": inc_id,
        "type": inc_type,
        "alertname": alertname,
        "instance": instance,
        "severity": severity,
        "description": description,
        "status": "open",
        "starts_at": starts_at,
        "created_at": ts.isoformat(),
        "updated_at": ts.isoformat(),
        "updates": [],
    }

    # Persist
    data = load_incidents()
    data["incidents"].append(incident)
    save_incidents(data)

    # Emit event
    emit_event("incident.created", source="alertmanager",
               incident_id=inc_id,
               payload={
                   "alertname": alertname,
                   "instance": instance,
                   "severity": severity,
                   "type": inc_type,
               })

    return incident


def update_incident(incident, alertname, severity, description, starts_at):
    """Update an existing incident with new alert data."""
    ts = datetime.now(timezone.utc)
    incident["updated_at"] = ts.isoformat()
    incident["severity"] = severity
    incident["updates"].append({
        "timestamp": ts.isoformat(),
        "source": "alertmanager",
        "description": description or f"Alert re-fired: {alertname}",
    })

    # Save
    data = load_incidents()
    for i, inc in enumerate(data["incidents"]):
        if inc["incident_id"] == incident["incident_id"]:
            data["incidents"][i] = incident
            break
    save_incidents(data)

    # Emit event
    emit_event("incident.updated", source="alertmanager",
               incident_id=incident["incident_id"],
               payload={
                   "alertname": alertname,
                   "severity": severity,
                   "update_count": len(incident["updates"]),
               })

    return incident


def ingest_alertmanager_payload(payload):
    """Process an Alertmanager webhook payload.

    Expects format:
    {
        "alerts": [
            {
                "status": "firing"|"resolved",
                "labels": {"alertname": "...", "severity": "...", "instance": "..."},
                "annotations": {"description": "..."},
                "startsAt": "2026-03-06T..."
            }
        ]
    }

    Returns list of processed incidents.
    """
    results = []
    alerts = payload.get("alerts", [])

    for alert in alerts:
        status = alert.get("status", "firing")
        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})

        alertname = labels.get("alertname", "unknown")
        severity = labels.get("severity", "warning")
        instance = labels.get("instance", "unknown")
        description = annotations.get("description", f"Alert: {alertname}")
        starts_at = alert.get("startsAt", datetime.now(timezone.utc).isoformat())

        if status == "resolved":
            # Find and close matching incident
            data = load_incidents()
            existing = find_active_incident(data, alertname, instance)
            if existing:
                existing["status"] = "resolved"
                existing["updated_at"] = datetime.now(timezone.utc).isoformat()
                existing["updates"].append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source": "alertmanager",
                    "description": f"Alert resolved: {alertname}",
                })
                for i, inc in enumerate(data["incidents"]):
                    if inc["incident_id"] == existing["incident_id"]:
                        data["incidents"][i] = existing
                        break
                save_incidents(data)
                emit_event("incident.updated", source="alertmanager",
                           incident_id=existing["incident_id"],
                           payload={"status": "resolved", "alertname": alertname})
                results.append({"action": "resolved", "incident": existing})
            continue

        # Firing alert — check for dedup
        data = load_incidents()
        existing = find_active_incident(data, alertname, instance)

        if existing:
            updated = update_incident(existing, alertname, severity, description, starts_at)
            results.append({"action": "updated", "incident": updated})
        else:
            created = create_incident(alertname, instance, severity, description, starts_at)
            results.append({"action": "created", "incident": created})

    return results
