# Infrastructure Backup Runbook — P37

## Quick Commands

```bash
oc infra status      # Check infrastructure health
oc infra inventory   # Collect node inventory via SSH
oc infra backup      # Export Proxmox configs + check OPNsense
oc infra tick        # Full pipeline
oc infra test        # Run acceptance tests
```

## What Gets Backed Up

| Component | Method | Frequency | Location |
|-----------|--------|-----------|----------|
| Node inventory | SSH auto-collect | Weekly | artifacts/infra/ |
| Proxmox configs | SSH export | Weekly | Lab/proxmox/cluster/configs/ |
| OPNsense config | Manual export | Monthly | Lab/network/firewall/opnsense/ |
| Switch configs | Manual export | As needed | Lab/network/switches/ |

## OPNsense Backup (Manual)

1. Open `https://10.1.1.1/` in browser
2. Navigate to System > Configuration > Backups
3. Click "Download configuration"
4. Save `config.xml` to `Lab/network/firewall/opnsense/config_backups/`

## Proxmox Export (Automated)

Exports from all 3 Proxmox hosts:
- `/etc/pve/storage.cfg`
- `/etc/pve/corosync.conf`
- `/etc/pve/datacenter.cfg`

Requires root SSH access from Nova. Passwords/tokens are automatically redacted.

## Switch Backups (Manual)

See per-switch instructions in `scripts/infra/switch_backup_placeholders/`

## Security

- All exported configs are redacted before storage
- No credentials stored in git
- Secret scan runs before any push
