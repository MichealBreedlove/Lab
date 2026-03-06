# Platform Status

## Priorities Completed

| Range | Description | Tests | Status |
|-------|-------------|-------|--------|
| P36 | Observability + Event Bus | 10 | PASS |
| P37 | Infrastructure Control Plane | 10 | PASS |
| P38 | Security Hygiene | 10 | PASS |
| P39 | Recruiter Export Pack | 10 | PASS |
| P40 | Continuous Verification | 10 | PASS |
| P41 | Hardening + Supply Chain | 10 | PASS |
| P42 | System Freeze v1.1 | 10 | PASS |
| P43 | Nova Control Plane | 10 | PASS |
| P44 | Drift Detection + Demo | 10 | PASS |
| P45 | Change Log System | 10 | PASS |
| P46 | Platform API v1 | 10 | PASS |
| P47 | Identity + Access Layer | 10 | PASS |
| P48 | API Auth Enforcement | 10 | PASS |
| P49 | Rate Limiting | 8 | PASS |
| P50 | Token Revocation | 7 | PASS |
| P51 | Service Accounts | 7 | PASS |
| P52 | TLS/Reverse Proxy | 7 | PASS |
| P53 | Self-Healing | 13 | PASS |
| P54 | Event Bus | 8 | PASS |
| P55 | AI Investigation | 9 | PASS |
| P56 | Git Remediation | 9 | PASS |
| P57 | Execution Policy | 11 | PASS |
| P58 | Alertmanager Ingestion | 10 | PASS |

**Total: 209+ acceptance tests across 23 priorities**

## Test Coverage

- Unit tests: Shell-based acceptance tests per priority
- Integration tests: API endpoint tests with real token auth
- Security tests: Secret scan on every priority
- Policy tests: RBAC enforcement verified at every API endpoint

## Platform API (v2.2)

| Endpoint | Method | Min Role | Description |
|----------|--------|----------|-------------|
| `/` | GET | viewer | Status + capabilities |
| `/topology` | GET | viewer | Network topology |
| `/events` | GET | viewer | Event bus query |
| `/incidents` | GET | viewer | Incident list |
| `/events/alertmanager` | POST | automation | Alert webhook |
| `/change` | POST | operator | Create change record |
| `/snapshot` | POST | operator | Trigger drift snapshot |
| `/incident` | POST | operator | Log manual incident |
| `/investigate` | POST | sre | AI investigation |
| `/remediation/artifact` | POST | sre | Generate remediation docs |
| `/recover` | POST | sre | Recovery engine |
| `/failover` | POST | sre | Service failover |
| `/chaos` | POST | sre | Chaos experiment |

## Incident System

- Alertmanager webhook ingestion with deduplication
- Automatic incident creation from monitoring alerts
- Status tracking: open → investigating → resolved
- Event bus integration for full audit trail

## AI Investigation System

- Deterministic playbook-based investigation engine
- 3 playbooks: api_down, node_unreachable, config_drift
- Multi-signal evidence gathering with confidence scoring
- Policy-gated execution decisions (auto_apply / require_review / deny)
- Git-backed remediation artifacts (summary, proposal, patch plan)
- Audit logging of all policy decisions

## Security Model

- Bearer token authentication on all endpoints
- RBAC: viewer < operator/automation < sre < admin
- Rate limiting per token with role-based quotas
- Service accounts with enable/disable lifecycle
- Token revocation with immediate effect
- Network restriction to 10.1.1.0/24
- TLS termination via Caddy reverse proxy
- Append-only audit logs

## Infrastructure

- **Controller**: Nova (10.1.1.21) — N305, 32GB DDR5
- **Workers**: Mira (10.1.1.22), Orin (10.1.1.23)
- **Hypervisors**: 3x Proxmox (10.1.1.2, .4, .5)
- **Firewall**: OPNsense (10.1.1.1)
- **Monitoring**: Prometheus, Grafana, Loki, node_exporter on all nodes
- **Dashboard**: Port 8080 (Nova), embedded in unified dashboard
