# Observability Runbook — P36

## Stack Components

| Service | Port | Purpose |
|---------|------|---------|
| Prometheus | 9090 | Metrics collection + alerting |
| Grafana | 3000 | Dashboards + visualization |
| Alertmanager | 9093 | Alert routing + notifications |
| Loki | 3100 | Log aggregation |
| Promtail | — | Log shipping agent |
| Node Exporter | 9100 | Host metrics |
| cAdvisor | 8081 | Container metrics |

All bound to `10.1.1.21` (Nova LAN) — not exposed publicly.

## Quick Start

```bash
# Install Docker + create directories (dry run)
oc obs install

# Install Docker + create directories (apply)
oc obs install --apply

# Start stack
oc obs up

# Check status
oc obs status

# View logs
oc obs logs

# Stop stack
oc obs down
```

## Event Bus

```bash
# Write an event
oc obs event write --type incident.opened --severity critical --node mira --message "Service down"

# Read recent events
oc obs event read --limit 20

# List event types
oc obs event types
```

## Alert Rules

- **NodeDown**: Target unreachable for 5 minutes (critical)
- **HighCPU**: >90% for 10 minutes (warning)
- **HighMemory**: >90% for 10 minutes (warning)
- **DiskCritical**: >90% root filesystem for 5 minutes (critical)
- **HighLoad**: Load ratio >3x for 15 minutes (warning)

## Adding Node Exporters to Mira/Orin

```bash
# On each Linux node:
sudo apt install prometheus-node-exporter
sudo systemctl enable prometheus-node-exporter
sudo systemctl start prometheus-node-exporter
```

## Troubleshooting

```bash
# Check container status
docker ps --filter "name=obs-"

# Check Prometheus targets
curl http://10.1.1.21:9090/api/v1/targets

# Check Alertmanager
curl http://10.1.1.21:9093/api/v2/status
```
