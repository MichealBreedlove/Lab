# Homelab Control Plane Runbook — P43

## Architecture

Nova is the single management node. All inventory collection and configuration backup runs from Nova via SSH/Ansible. GamingPC (Jasper) remains the operator console.

```
┌──────────────────────────────────────────────┐
│              GamingPC (Jasper)                │
│         Operator Console + GPU               │
│     ssh nova "oc controlplane tick"          │
└──────────────┬───────────────────────────────┘
               │ SSH
┌──────────────▼───────────────────────────────┐
│              Nova (Controller)               │
│    ~/homelab-controller (source of truth)    │
│    Ansible playbooks + scheduled ticks       │
├──────────────┬──────────┬──────────┬─────────┤
│  SSH         │  SSH     │  SSH     │  SSH    │
▼              ▼          ▼          ▼         │
OPNsense    Proxmox-1  Proxmox-2  Proxmox-3   │
10.1.1.1    10.1.1.2   10.1.1.4   10.1.1.5    │
├──────────────┼──────────┼──────────┤         │
Mira         Orin       Switches               │
10.1.1.22    10.1.1.23  (when managed)         │
└──────────────────────────────────────────────┘
```

## Quick Commands

### From Nova
```bash
oc controlplane tick         # Quick tick (nodes + BIOS)
oc controlplane full         # Full tick (all devices)
oc controlplane status       # Show last tick results
oc controlplane connectivity # Scan all device ports
oc controlplane test         # Run acceptance tests
```

### From GamingPC (PowerShell)
```powershell
ssh nova "cd ~/homelab-controller && ./scripts/controlplane/homelab_tick.sh quick"
ssh nova "cd ~/homelab-controller && ./scripts/controlplane/homelab_tick.sh full push"
```

## What Gets Collected

| Domain | Source | Method | Frequency |
|--------|--------|--------|-----------|
| Node BIOS/firmware | nova, mira, orin | dmidecode via SSH | Daily |
| OPNsense config | 10.1.1.1 | SSH (config.xml + commands) | Weekly |
| Proxmox configs | 3 PVE hosts | SSH (pveversion, storage.cfg, etc.) | Weekly |
| Switch configs | When managed | SSH (show running-config) | Weekly |

## Credentials

Secrets stored at `~/.config/homelab/secrets.env` (chmod 600, never committed):

```bash
# Optional — only needed for API-based access
OPNSENSE_API_KEY=your_key_here
OPNSENSE_API_SECRET=your_secret_here

# Proxmox API token (optional, SSH preferred)
# PVE_API_TOKEN=user@pam!token=uuid
```

## Safety Model

- **Read-only by default** — all playbooks only collect data
- **Apply playbook** requires break-glass token (<30 min fresh)
- **Sanitize** runs before any commit (passwords, tokens, keys stripped)
- **No destructive changes** without explicit approval
- **No secrets in git** — ever

## Systemd Timer

Daily quick tick + weekly full tick via user-level systemd timers on Nova.

## GitHub Backup

Sanitized artifacts push to `MichealBreedlove/Lab` under:
- `/network/opnsense/inventory/`
- `/proxmox/<node>/`
- `/network/switches/<vendor_model>/`
- `/bios/<node>/`
