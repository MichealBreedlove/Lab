# Observability Stack

Prometheus + Grafana running on CT 303 (Mira, 10.1.1.25).

## Prometheus Targets (13 total)

| Instance | IP:Port | Status |
|----------|---------|--------|
| monitoring | 10.1.1.25:9100 | ✅ up |
| PROXMOX | 10.1.1.2:9100 | ✅ up |
| PROXMOX-2 | 10.1.1.4:9100 | ✅ up |
| PROXMOX-3 | 10.1.1.5:9100 | ✅ up |
| Nova | 10.1.1.21:9100 | ✅ up |
| Mira | 10.1.1.22:9100 | ✅ up |
| Orin | 10.1.1.23:9100 | ✅ up |
| TrueNAS | 10.1.1.11:9100 | ✅ up |
| Immich | 10.1.1.30:9100 | ✅ up |
| Plex | 10.1.1.31:9100 | ✅ up |
| UniFi | 10.1.1.100:9100 | ✅ up |
| OPNsense | 10.1.1.1:9100 | ✅ up |
| prometheus | localhost:9090 | ✅ up |

## Grafana Dashboards

- **Node Exporter Full** — `/d/rYdddlPWk/` (per-node deep dive)
- **Prometheus Stats** — `/d/bffnnj0jpoq9sf/`
- **Node Exporter EN** — `/d/xfpJB9FGz/` (clean cluster overview)

Access: `http://10.1.1.25:3000`

## Alert Rules (8)

| Alert | Threshold |
|-------|-----------|
| NodeDown | >2m unreachable → critical |
| HighCPU | >85% for 5m → warning |
| HighMemory | >90% for 5m → warning |
| DiskWarning | >80% for 5m → warning |
| DiskCritical | >90% for 2m → critical |
| NodeReboot | uptime <5min → info |
| HighDiskIOWait | >20% for 5m → warning |
| NetworkErrors | >10 errors/s for 5m → warning |

## Special Notes

- **TrueNAS node_exporter**: `/mnt/Tank/node_exporter` (survives upgrades); systemd unit `/etc/systemd/system/node_exporter.service`
- **OPNsense node_exporter**: FreeBSD `os-node_exporter` package; `service node_exporter start`
- **Immich node_exporter**: CT 502 on Orin; installed 2026-03-10
- **Prometheus config**: `/etc/prometheus/prometheus.yml` inside CT 303
- **Alert rules**: `/etc/prometheus/alert_rules.yml` inside CT 303
- **Reload**: `curl -X POST http://10.1.1.25:9090/-/reload`
