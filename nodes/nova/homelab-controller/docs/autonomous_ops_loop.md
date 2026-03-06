# Autonomous Operations Loop

## Schedule

| Task | Interval | Target Role | Priority |
|------|----------|-------------|----------|
| Cluster health scan | 15 min | proxmox_optimizer | normal |
| Firewall audit | 12 hours | network_optimizer | normal |
| WiFi analysis | 24 hours | network_optimizer | low |
| Proxmox audit | 24 hours | proxmox_optimizer | normal |
| Drift detection | 6 hours | infra_scanner | normal |
| Daily scorecard | 24 hours | coordinator | low |

## Scorecard Metrics

- **Cluster Health**: % of agents online
- **Task Completion**: % of tasks completed vs total
- **Automation Maturity**: baseline score for having the system running

## What Runs Automatically

- Audits (firewall, WiFi, Proxmox, drift)
- Documentation generation
- Artifact generation
- Backup/config snapshots
- Scorecard generation
- Low-risk Proxmox hygiene (tags, notes, metadata)

## What Requires Approval

- Investigation actions
- Remediation execution
- Policy changes
- Any infrastructure-modifying action
- High-risk task reassignment
