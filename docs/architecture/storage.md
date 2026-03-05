# Storage Architecture

## Local Storage
Each node has local NVMe/SSD for OS and working data.

## TrueNAS (if applicable)
- Shared datasets for model weights, backups
- NFS/SMB shares mounted on compute nodes

## Backup Strategy
- Each node auto-commits sanitized state to GitHub daily
- Restore runbook: `docs/runbooks/restore.md`
