# Roadmap

Planned improvements for the lab infrastructure.

## In Progress

- [ ] Grafana dashboards for SLO visualization and burn-rate trends
- [ ] Automated restore testing (scheduled validation of backup integrity)
- [ ] Expand test coverage to 50+ acceptance tests

## Planned

- [ ] SIEM integration (centralized log aggregation and correlation)
- [ ] Alertmanager integration for multi-channel incident notification
- [ ] Chaos engineering expansion (network partition, disk pressure scenarios)
- [ ] Infrastructure-as-code migration (Terraform for Proxmox provisioning)
- [ ] Dedicated 10 GbE inference node (Jasper hardware migration)
- [ ] Container orchestration evaluation (K3s or Nomad on Proxmox)

## Completed

- [x] SLO evaluation with error budgets and burn-rate alerting
- [x] Incident management with auto-generated postmortems
- [x] GitOps backup system with secret scanning CI gate
- [x] Safety gates blocking automation on budget exhaustion
- [x] 38+ acceptance tests across all pipeline components
- [x] Per-node segregated backup with credential sanitization
- [x] GitHub Pages documentation site
- [x] Portfolio integration with case studies
