# Disaster Recovery

## Overview

The DR system provides one-command restore capability with automated validation. Every restore operation requires a break-glass token and produces a full evidence pack.

## Components

| Component | Path | Purpose |
|-----------|------|---------|
| `dr_preflight.py` | `scripts/dr/` | Pre-restore validation (node health, storage, network) |
| `dr_restore.py` | `scripts/dr/` | Orchestrated restore from TrueNAS snapshots |
| `dr_validate.py` | `scripts/dr/` | Post-restore verification (services, data integrity) |
| `dr_drill.py` | `scripts/dr/` | Scheduled DR drill with evidence generation |
| `dr_dashboard.py` | `scripts/dr/` | DR readiness dashboard panel |

## Break-Glass Protocol

Destructive restore operations require a fresh break-glass token:

1. Token generated to `config/break_glass.token`
2. Token expires after 30 minutes
3. Token is never committed to git
4. All token usage is logged

## Restore Workflow

```
1. Preflight   → Verify node health, storage availability, network connectivity
2. Token       → Generate or verify break-glass token
3. Restore     → Execute restore from latest verified backup
4. Validate    → Run post-restore checks (services, ports, data)
5. Evidence    → Generate evidence pack with timestamps and results
```

## DR Drill Schedule

- Full DR drill available via `oc demo run` (simulation mode)
- Drills produce change log entries and evidence packs
- Results tracked in `artifacts/demos/`

## Backup Sources

| Source | Method | Location |
|--------|--------|----------|
| OPNsense config | SSH export | `artifacts/controlplane/opnsense/` |
| Proxmox configs | SSH + API | `artifacts/controlplane/proxmox/` |
| Node configs | SSH inventory | `state/observed/` |
| Controller state | Git (GitHub) | `MichealBreedlove/Lab` |

## Readiness Model

DR readiness is assessed on:
- Last successful backup age
- Last successful restore test
- Node connectivity (all nodes reachable)
- Storage availability (TrueNAS NFS accessible)
- Break-glass token mechanism functional

## Runbooks

- Full restore: `oc dr restore --target <node>`
- Drill: `oc dr drill`
- Preflight only: `oc dr preflight`
- Validate: `oc dr validate`
