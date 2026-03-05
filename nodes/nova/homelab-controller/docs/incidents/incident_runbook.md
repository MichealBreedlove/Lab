# Incident Runbook

## Declaration
Incidents are auto-opened by the tick pipeline when triggers fire:
- **SLO high burn rate** (>6x in 1h window)
- **SLO budget exhausted** (0% remaining)
- **Gatekeeper DENY** (action blocked by safety gates)
- **Chaos failure** (>30% experiment failure rate)
- **Planner RED** (cluster in critical state)

Manual declaration:
```bash
oc incident open --title "Description" --severity SEV1
```

## Severity Levels

| Level | Name | Description | Auto-close |
|-------|------|-------------|------------|
| SEV0 | Critical | Total outage or data loss risk | Never |
| SEV1 | Major | Significant multi-service degradation | 24h |
| SEV2 | Minor | Single service, limited impact | 12h |
| SEV3 | Info | Anomaly observed, no user impact | 6h |

## Triage
1. Check `oc incident status` for active incident details
2. Check `oc slo status` for SLO health
3. Check `oc incident timeline` for event sequence
4. Identify blast radius and SPOFs

## Mitigation
1. If SLO-triggered: check which service is degraded
2. Use P23 action approvals for safe remediation
3. Add notes as you go: `oc incident note "Restarted ollama on mira"`
4. If action is gated, use break-glass if justified

## Resolution
```bash
oc incident close --summary "Root cause: Ollama OOM on mira. Restarted service, increased memory limit."
```

## Postmortem
After closing, generate postmortem:
```bash
oc incident postmortem
```

Review and fill in:
- Root cause analysis
- Lessons learned
- Action items with owners and due dates

## Cooldowns
After an incident opens for a trigger, the same trigger won't fire again for:
- SEV0: 60 minutes
- SEV1: 30 minutes
- SEV2: 15 minutes
- SEV3: 5 minutes
