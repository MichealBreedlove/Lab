# Reliability Engineering

## SLO Framework

6 service-level objectives tracked across 5 sliding time windows (1h, 6h, 24h, 7d, 30d).

### Monitored Services

| Service | SLO Target | Metric |
|---|---|---|
| Gateway availability | 99.9% | HTTP health checks |
| Ollama availability | 99.5% | Inference endpoint response |
| Dashboard availability | 99.0% | Web UI accessibility |
| Backup freshness | < 24h | Last commit timestamp |
| Agent responsiveness | < 30s | OpenClaw ping latency |
| Node health | 100% | System resource thresholds |

## Burn-Rate Alerting

The burn-rate calculator detects when error budget consumption is accelerating:

- **< 1.0x** — Normal consumption
- **1.0x–2.0x** — Warning, budget depleting faster than expected
- **> 2.0x** — Critical, SLO breach likely within window

## Incident Management

Automated pipeline:

1. **Detection** — SLO breach or anomaly triggers incident creation
2. **Classification** — Severity assigned based on impact and budget state
3. **Tracking** — Timeline recorded with all state changes
4. **Resolution** — TTR tracked, root cause documented
5. **Postmortem** — Auto-generated with timeline, cause, and action items

## Safety Gates

The gatekeeper system blocks risky automation when:

- Error budget is exhausted for any service
- Active incidents are unresolved
- Burn rate exceeds configured thresholds

This prevents cascading failures from automated actions.

## Test Coverage

38+ acceptance tests validate:

- SLI computation accuracy
- SLO evaluation logic
- Burn-rate calculations
- Incident lifecycle state machine
- Postmortem generation
- Safety gate decisions
