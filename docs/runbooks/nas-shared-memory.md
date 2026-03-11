# Runbook: NAS Shared Memory & Hourly Backups

**Date:** 2026-03-10  
**Status:** Active

## Overview

Each cluster node writes a per-node daily memory file to the NAS every hour. This creates shared context visible to all nodes and provides backup continuity across sessions.

## NAS Structure

```
/mnt/Tank/openclaw/
├── shared/
│   ├── memory/
│   │   ├── YYYY-MM-DD.md          # Jasper's daily memory (canonical)
│   │   ├── YYYY-MM-DD-jasper.md   # Jasper per-node copy
│   │   ├── YYYY-MM-DD-nova.md     # Nova agent VM
│   │   ├── YYYY-MM-DD-mira.md     # Mira agent VM
│   │   └── YYYY-MM-DD-orin.md     # Orin agent VM
│   ├── node_backup.sh             # Deployed script
│   └── MEMORY.md                  # Long-term shared memory
├── agents/
│   ├── jasper/backups/            # Jasper workspace backups
│   ├── nova/, mira/, orin/        # Per-node agent data
```

## Backup Scripts

### Agent VMs (nova, mira, orin)
- **Script:** `/opt/node_backup.sh` on each VM (sourced from NAS)
- **Cron:** `0 * * * *` (every hour on the hour)
- **Log:** `/var/log/node_backup.log`
- **Writes:** `/mnt/openclaw-shared/memory/YYYY-MM-DD-{node}.md`

### Jasper (Windows)
- **Script:** `C:\Users\mikej\.openclaw\workspace\scripts\nas_backup.ps1`
- **Cron:** OpenClaw cron job ID `a9254aa1` (hourly)
- **Writes:** `Z:\agents\jasper\backups\` + `Z:\shared\memory\YYYY-MM-DD-jasper.md`

## Internet Watchdog

If Jasper loses internet connectivity, OpenClaw automatically switches to local Ollama model:
- **Script:** `scripts\internet_watchdog.ps1`
- **Fallback model:** `ollama/qwen3.5:35b`
- **Check interval:** Every 2 minutes
- **Task:** `OpenClaw-InternetWatchdog` (Windows Task Scheduler, runs hidden via VBScript)
- **Reverts** to `anthropic/claude-sonnet-4-6` when internet is restored

## NAS Mounts

| Host | Mount Path | NFS Export |
|------|-----------|------------|
| nova VM | `/mnt/openclaw-shared` | `10.1.1.11:/mnt/Tank/openclaw/shared` |
| mira VM | `/mnt/openclaw-shared` | `10.1.1.11:/mnt/Tank/openclaw/shared` |
| orin VM | `/mnt/openclaw-shared` | `10.1.1.11:/mnt/Tank/openclaw/shared` |
| Jasper | `Z:\` | `\\TRUENAS\openclaw` (SMB) |
