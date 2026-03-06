# Operations

## Daily Workflow

Nova runs automated ticks via systemd timers:
- **Quick tick** (daily 6 AM) — Inventory collection, drift check, security scan, dashboard update
- **Full tick** (Sunday 3 AM) — Full OPNsense/Proxmox inventory, supply chain audit, release verification

All artifacts are written to `nodes/nova/homelab-controller/artifacts/` and dashboard JSON updates to `dashboard/static/data/`.

## CLI Reference

The `oc` command (`bin/oc.sh`) is the single entry point for all operations:

### Drift Detection
```bash
oc drift run          # Full pipeline: render desired → collect observed → diff
oc drift status       # Show current drift status (GREEN/YELLOW/RED)
```

### Change Management
```bash
oc change list              # List recent changes
oc change show <CHG-ID>     # View a specific change report
oc change create <trigger> <summary>  # Create new change entry
oc change validate <CHG-ID> # Run connectivity validation
```

### Platform API
```bash
oc platform status    # Check if API is running
oc platform start     # Install and start API service
oc platform stop      # Stop API service
oc platform chaos     # Trigger chaos scenario via API
oc platform change    # Trigger change pipeline via API
oc platform snapshot  # Trigger full snapshot via API
```

### Observability
```bash
oc obs up             # Start Prometheus/Grafana/Loki stack
oc obs down           # Stop stack
oc obs status         # Check container status
oc obs logs           # View recent logs
oc obs export         # Export metrics snapshot
```

### Reliability Demos
```bash
oc demo list          # List available scenarios
oc demo run <name>    # Run a scenario end-to-end
```

### Infrastructure
```bash
oc infra scan         # Run infrastructure inventory scan
oc infra status       # Show infrastructure health
```

### Testing
```bash
oc test all           # Run all test suites
oc test p44           # Run P44 platform upgrade tests
oc test p45           # Run P45 change system tests
oc test p46           # Run P46 platform API tests
```

## Artifact Locations

| Artifact | Path |
|----------|------|
| Drift reports | `state/drift/drift_report.{json,md}` |
| Change logs | `changes/CHG-*/` |
| Demo artifacts | `artifacts/demos/` |
| Observability status | `artifacts/observability/` |
| Infrastructure inventory | `artifacts/controlplane/` |
| Security scans | `artifacts/security/` |
| Release audits | `artifacts/release/` |
| Dashboard data | `dashboard/static/data/` |

## Dashboards

| Dashboard | URL | Description |
|-----------|-----|-------------|
| Nova Dashboard | `http://10.1.1.21:8080` | Homelab controller status |
| Platform API | `http://10.1.1.21:8081` | Control interface |
| Grafana | `http://10.1.1.21:3000` | Metrics and logs |
| Prometheus | `http://10.1.1.21:9090` | Metric queries |
| Unified Dashboard | `http://10.1.1.150:18080` | Combined view |

## Monitoring

Prometheus scrapes:
- `node_exporter` on Nova (:9100), Mira, Orin
- Alert rules for node down, high CPU, disk pressure
- Grafana dashboards for node health and OpenClaw cluster health
- Loki + Promtail for centralized log aggregation
