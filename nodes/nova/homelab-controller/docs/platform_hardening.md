# Platform Hardening Checklist

Post-P58 stabilization tasks for production readiness.

## Storage & State

- [ ] **Persistent rate limiting backend** — File-backed or Redis sliding window state that survives API restarts
- [ ] **Event bus rotation** — Rotate `event_log.jsonl` daily or by size (>10MB); archive to `data/events/archive/`
- [ ] **Platform state backup** — Include `artifacts/identity/`, `data/events/`, `data/auth/`, `config/` in automated backup pipeline
- [ ] **Audit log rotation** — Rotate `api_audit.jsonl` and `policy_audit.jsonl` monthly

## Disaster Recovery

- [ ] **DR test for identity layer** — Verify token store restore from backup
- [ ] **DR test for incident data** — Verify incidents.json restore
- [ ] **Event bus replay** — Confirm events can be replayed from JSONL backup
- [ ] **Recovery engine stress test** — Simulate 10+ concurrent incidents; verify no race conditions

## TLS & Network Security

- [ ] **TLS certificate rotation** — Document Caddy auto-renewal verification steps
- [ ] **mTLS between nodes** — Client certificates for Nova-to-Mira/Orin recovery commands
- [ ] **API bind restriction** — Verify 10.1.1.0/24 enforcement under all entry paths
- [ ] **Firewall audit** — Confirm UFW rules match expected ports (8080, 8081, 3000, 9090, 3100, 9100)

## Monitoring & Observability

- [ ] **Monitoring coverage validation** — All 6 nodes (3 PVE + 3 Linux) reporting to Prometheus
- [ ] **Alert rules audit** — Verify `alert_rules.yml` covers: node down, disk >90%, API latency >5s
- [ ] **Grafana dashboard review** — Confirm dashboards show: temps, disk, CPU, memory, API latency
- [ ] **Loki log ingestion** — Verify platform API logs flowing to Loki

## Identity & Access

- [ ] **Token rotation policy** — Auto-expire tokens >7 days; notify on approaching expiry
- [ ] **Service account audit** — Review active service accounts quarterly
- [ ] **Failed auth alerting** — Alert on >10 failed auth attempts in 5 minutes
- [ ] **Audit log review** — Weekly review of policy_audit.jsonl for anomalies
