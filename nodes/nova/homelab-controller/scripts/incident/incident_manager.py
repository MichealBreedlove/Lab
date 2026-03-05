#!/usr/bin/env python3
"""incident_manager.py — Core incident engine + CLI.

Commands: open, note, timeline, close, status, tick
Tick reads SLO outputs + gatekeeper decisions, auto-opens/updates incidents.
"""

import sys
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List

from incident_state import (
    create_incident, load_incident, update_incident,
    add_timeline_event, close_incident, list_incidents,
    get_active_incident, is_in_cooldown, load_policy,
    ARTIFACTS_DIR
)

ROOT_DIR = Path(__file__).parent.parent.parent
SLO_CURRENT = ROOT_DIR / "artifacts" / "slo" / "current.json"
GATE_LOG = ROOT_DIR / "artifacts" / "gatekeeper" / "decisions.jsonl"


def _load_json(path: Path) -> Optional[dict]:
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


def _read_last_jsonl(path: Path, n: int = 5) -> List[dict]:
    if not path.exists():
        return []
    lines = path.read_text().strip().split("\n")
    result = []
    for line in lines[-n:]:
        if line.strip():
            try:
                result.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return result


def cmd_status():
    """Show current incident status."""
    active = get_active_incident()
    if not active:
        print("No active incidents. ✅")
        return

    print(f"🚨 ACTIVE INCIDENT: {active['id']}")
    print(f"   Severity:  {active['severity']}")
    print(f"   Title:     {active['title']}")
    print(f"   Trigger:   {active['trigger']}")
    print(f"   Opened:    {active['opened_at']}")
    print(f"   Status:    {active['status']}")
    if active.get("blast_radius"):
        print(f"   Blast:     {', '.join(active['blast_radius'])}")
    if active.get("spof_tags"):
        print(f"   SPOF:      {', '.join(active['spof_tags'])}")
    print(f"   Timeline:  {len(active.get('timeline', []))} events")


def cmd_open(args):
    """Manually open an incident."""
    inc = create_incident(
        trigger="manual",
        severity=args.severity or "SEV2",
        title=args.title or "Manual incident",
        description=args.description or ""
    )
    print(f"✅ Incident opened: {inc['id']} ({inc['severity']})")
    print(f"   Title: {inc['title']}")


def cmd_note(args):
    """Add a note to an incident."""
    incident_id = args.incident_id
    if not incident_id:
        active = get_active_incident()
        if not active:
            print("No active incident. Specify --incident-id.")
            return
        incident_id = active["id"]

    inc = add_timeline_event(
        incident_id,
        event="note",
        detail=args.note,
        actor=args.actor or "operator"
    )
    print(f"📝 Note added to {incident_id}")


def cmd_close(args):
    """Close an incident."""
    incident_id = args.incident_id
    if not incident_id:
        active = get_active_incident()
        if not active:
            print("No active incident to close.")
            return
        incident_id = active["id"]

    inc = close_incident(
        incident_id,
        resolution_summary=args.summary or "Resolved",
        actor=args.actor or "operator"
    )
    print(f"✅ Incident {incident_id} closed.")
    print(f"   Resolution: {inc['resolution_summary']}")


def cmd_timeline(args):
    """Show timeline for an incident."""
    incident_id = args.incident_id
    if not incident_id:
        active = get_active_incident()
        if not active:
            print("No active incident.")
            return
        incident_id = active["id"]

    inc = load_incident(incident_id)
    if not inc:
        print(f"Incident {incident_id} not found.")
        return

    print(f"📋 Timeline: {inc['id']} — {inc['title']}")
    print(f"   Status: {inc['status']} | Severity: {inc['severity']}")
    print()
    for event in inc.get("timeline", []):
        ts = event.get("timestamp", "?")[:19]
        ev = event.get("event", "?")
        detail = event.get("detail", "")
        actor = event.get("actor", "")
        print(f"  [{ts}] {ev}: {detail} ({actor})")


def cmd_list_incidents(args):
    """List all incidents."""
    status_filter = args.status if hasattr(args, "status") else None
    incidents = list_incidents(status=status_filter)
    if not incidents:
        print("No incidents found.")
        return

    for inc in incidents[:20]:
        status_icon = {"open": "🔴", "resolved": "✅", "mitigated": "🟡"}.get(
            inc.get("status"), "❓")
        print(f"  {status_icon} {inc['id']} [{inc['severity']}] "
              f"{inc['title']} ({inc['status']})")


def cmd_tick():
    """Auto-check triggers and open/update incidents.

    Reads SLO current + gatekeeper log. Opens incidents on:
    - SLO high burn rate
    - SLO budget exhausted
    - Gatekeeper DENY
    """
    policy = load_policy()
    if not policy.get("enabled", True):
        print("Incident management disabled.")
        return

    triggers = policy.get("triggers", {})
    opened = []

    # Check SLO triggers
    slo_data = _load_json(SLO_CURRENT)
    if slo_data:
        for slo_id, slo in slo_data.get("slos", {}).items():
            budget = slo.get("budget", {})
            burn_rates = slo.get("burn_rates", {})

            # Trigger: SLO budget exhausted
            if triggers.get("slo_budget_exhausted", {}).get("enabled"):
                if budget.get("budget_exhausted"):
                    trigger_name = "slo_budget_exhausted"
                    if not is_in_cooldown(trigger_name):
                        sev = triggers[trigger_name].get("severity", "SEV1")
                        inc = create_incident(
                            trigger=trigger_name,
                            severity=sev,
                            title=f"SLO budget exhausted: {slo.get('name', slo_id)}",
                            description=f"Error budget at {budget.get('remaining_budget_pct', 0)}%",
                            slo_id=slo_id,
                            evidence_paths=[str(SLO_CURRENT)]
                        )
                        opened.append(inc)

            # Trigger: SLO high burn
            burn_config = triggers.get("slo_high_burn", {})
            if burn_config.get("enabled"):
                window = burn_config.get("window", "rolling_1h")
                min_burn = burn_config.get("min_burn_rate", 6.0)
                w = burn_rates.get(window, {})
                if w.get("burn_rate") and w["burn_rate"] >= min_burn:
                    trigger_name = "slo_high_burn"
                    if not is_in_cooldown(trigger_name):
                        sev = burn_config.get("severity", "SEV1")
                        inc = create_incident(
                            trigger=trigger_name,
                            severity=sev,
                            title=f"High burn rate: {slo.get('name', slo_id)} "
                                  f"({w['burn_rate']:.1f}x in {window})",
                            description=f"Burn rate {w['burn_rate']:.1f}x exceeds "
                                       f"threshold {min_burn}x",
                            slo_id=slo_id,
                            evidence_paths=[str(SLO_CURRENT)]
                        )
                        opened.append(inc)

    # Check gatekeeper triggers
    if triggers.get("gatekeeper_deny", {}).get("enabled"):
        gate_entries = _read_last_jsonl(GATE_LOG, 10)
        for entry in gate_entries:
            if entry.get("decision") == "DENY":
                trigger_name = "gatekeeper_deny"
                if not is_in_cooldown(trigger_name):
                    sev = triggers[trigger_name].get("severity", "SEV2")
                    inc = create_incident(
                        trigger=trigger_name,
                        severity=sev,
                        title=f"Gatekeeper DENY: {entry.get('reason', 'unknown')}",
                        description=json.dumps(entry, default=str),
                        evidence_paths=[str(GATE_LOG)]
                    )
                    opened.append(inc)
                    break  # Only one incident per tick for gate denies

    # Auto-close expired incidents
    for inc in list_incidents(status="open"):
        sev = inc.get("severity", "SEV2")
        levels = policy.get("severity_levels", {})
        auto_close_hours = levels.get(sev, {}).get("auto_close_hours")
        if auto_close_hours:
            try:
                opened_dt = datetime.fromisoformat(inc["opened_at"])
                elapsed_hours = (datetime.now(timezone.utc) - opened_dt).total_seconds() / 3600
                if elapsed_hours >= auto_close_hours:
                    close_incident(
                        inc["id"],
                        resolution_summary=f"Auto-closed after {auto_close_hours}h",
                        actor="system"
                    )
                    print(f"  Auto-closed: {inc['id']} (elapsed {elapsed_hours:.1f}h)")
            except (ValueError, KeyError):
                pass

    # Summary
    if opened:
        for inc in opened:
            print(f"🚨 Opened: {inc['id']} [{inc['severity']}] {inc['title']}")
    else:
        active = get_active_incident()
        if active:
            print(f"No new incidents. Active: {active['id']} ({active['severity']})")
        else:
            print("No new incidents. All clear. ✅")


def main():
    parser = argparse.ArgumentParser(description="Incident Commander")
    sub = parser.add_subparsers(dest="command")

    # status
    sub.add_parser("status", help="Show active incident")

    # open
    p_open = sub.add_parser("open", help="Open a new incident")
    p_open.add_argument("--title", "-t", required=True)
    p_open.add_argument("--severity", "-s", default="SEV2")
    p_open.add_argument("--description", "-d", default="")

    # note
    p_note = sub.add_parser("note", help="Add a note")
    p_note.add_argument("note", help="Note text")
    p_note.add_argument("--incident-id", "-i", default=None)
    p_note.add_argument("--actor", "-a", default="operator")

    # close
    p_close = sub.add_parser("close", help="Close an incident")
    p_close.add_argument("--incident-id", "-i", default=None)
    p_close.add_argument("--summary", "-s", default="Resolved")
    p_close.add_argument("--actor", "-a", default="operator")

    # timeline
    p_tl = sub.add_parser("timeline", help="Show timeline")
    p_tl.add_argument("--incident-id", "-i", default=None)

    # list
    p_list = sub.add_parser("list", help="List incidents")
    p_list.add_argument("--status", default=None)

    # tick
    sub.add_parser("tick", help="Auto-check triggers")

    args = parser.parse_args()

    if args.command == "status":
        cmd_status()
    elif args.command == "open":
        cmd_open(args)
    elif args.command == "note":
        cmd_note(args)
    elif args.command == "close":
        cmd_close(args)
    elif args.command == "timeline":
        cmd_timeline(args)
    elif args.command == "list":
        cmd_list_incidents(args)
    elif args.command == "tick":
        cmd_tick()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
