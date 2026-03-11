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
| HighMemory | >95% for 5m → warning |
| DiskWarning | >88% for 10m → warning |
| DiskCritical | >90% for 2m → critical |
| NodeReboot | uptime <5min → info |
| HighDiskIOWait | >20% for 5m → warning |
| NetworkErrors | >10 errors/s for 5m → warning |

> **Threshold notes:** HighMemory raised to 95% — PROXMOX runs at design capacity with TrueNAS VM + Nova VM filling 32GB host. DiskWarning raised to 88% / 10m window — agent VMs are 32–64GB; 80% is normal operating range after log cleanup.

## Special Notes

- **TrueNAS node_exporter**: `/mnt/Tank/node_exporter` (survives upgrades); systemd unit `/etc/systemd/system/node_exporter.service`
- **OPNsense node_exporter**: FreeBSD `os-node_exporter` package; `service node_exporter start`
- **Immich node_exporter**: CT 502 on Orin; installed 2026-03-10
- **Prometheus config**: `/etc/prometheus/prometheus.yml` inside CT 303
- **Alert rules**: `/etc/prometheus/alert_rules.yml` inside CT 303
- **Reload**: `curl -X POST http://10.1.1.25:9090/-/reload`

## Automation & Tooling

### Morning Brief
Daily cluster health summary delivered at 8 AM Pacific via OpenClaw cron job.

Covers: Prometheus target health, active alerts, cluster task counts, Jasper GPU stats, disk usage, local weather.

Script: `scripts/morning_brief.ps1` — delivered to TUI + Telegram automatically.

### Semantic Memory Search
Local vector search over all OpenClaw memory files.

- Backend: ChromaDB + Ollama `nomic-embed-text` (fully offline, no API cost)
- 315 chunks indexed across daily notes, SOUL.md, USER.md, AGENTS.md, TOOLS.md
- DB: `C:\Users\mikej\.memsearch\chroma\`

```bash
python3 scripts/memory_search.py search "your question"
python3 scripts/memory_search.py index   # re-index after new memory files
python3 scripts/memory_search.py stats
```

### Secret Scanning
TruffleHog v3.93.8 runs automatically on every `git push` via pre-push hook.

- Binary: `C:\Users\mikej\tools\trufflehog.exe`
- Hook: `.git/hooks/pre-push`
- Blocks push if verified secrets detected; passes cleanly if none found

### Log Rotation (Agent VMs)
All three agent VMs (nova/mira/orin) have permanent log caps:

- journald: 500MB max, 2-week retention (`/etc/systemd/journald.conf.d/size-limit.conf`)
- Weekly cron: journal vacuum + apt clean + docker prune (`/etc/cron.weekly/clean-logs`)

### Disk Sizing
- Agent VMs: 64GB root disk (nova expanded 2026-03-11; mira/orin pending if needed)
- Disk warning threshold: 88% — provides ~8GB headroom on 64GB disks before alert
