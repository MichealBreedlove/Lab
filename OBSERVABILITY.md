# Observability

## Stack

The observability stack runs on Nova via Docker Compose:

| Service | Port | Image | Purpose |
|---------|------|-------|---------|
| **Prometheus** | 9090 | `prom/prometheus:latest` | Metric collection and alerting |
| **Grafana** | 3000 | `grafana/grafana:latest` | Dashboards and visualization |
| **Loki** | 3100 | `grafana/loki:latest` | Log aggregation |
| **Promtail** | — | `grafana/promtail:latest` | Log shipping to Loki |
| **Node Exporter** | 9100 | `prom/node-exporter:latest` | Host metrics (CPU, memory, disk, network) |

## Access

All services are LAN-restricted (10.1.1.0/24 via UFW):

- Grafana: `http://10.1.1.21:3000` (default credentials: admin/homelab)
- Prometheus: `http://10.1.1.21:9090`
- Loki: `http://10.1.1.21:3100` (API only)

## What Is Monitored

### Node Metrics (via node_exporter)
- CPU utilization, load average
- Memory usage and swap
- Disk space and I/O
- Network traffic and errors
- System uptime

### Alert Rules
- `NodeDown` — Node exporter unreachable for >2 minutes
- `HighCPU` — CPU usage >90% for 5 minutes
- `DiskPressure` — Disk usage >85%
- `HighMemory` — Memory usage >90% for 5 minutes

### Scrape Targets
- Nova (10.1.1.21:9100)
- Mira (10.1.1.22:9100) — requires node_exporter install
- Orin (10.1.1.23:9100) — requires node_exporter install

## Grafana Dashboards

Two pre-provisioned dashboards:

1. **Node Health** — Per-node CPU, memory, disk, network panels
2. **OpenClaw Health** — Cluster-level view with node status, gateway health, inference metrics

Dashboards are provisioned automatically from `scripts/observability/dashboards/`.

## Log Aggregation

Promtail ships logs from `/var/log/` on Nova to Loki. Queryable via Grafana's Explore view with LogQL.

## Management

```bash
oc obs up        # Start all containers
oc obs down      # Stop all containers
oc obs status    # Show container status
oc obs logs      # Tail recent logs
oc obs export    # Export current metrics snapshot
```

## Configuration Files

| File | Purpose |
|------|---------|
| `scripts/observability/docker-compose.yml` | Stack definition |
| `scripts/observability/prometheus.yml` | Scrape config + targets |
| `scripts/observability/alert_rules.yml` | Alerting rules |
| `scripts/observability/loki.yml` | Loki configuration |
| `scripts/observability/promtail.yml` | Log shipping config |
| `scripts/observability/dashboards/` | Grafana dashboard JSON |
