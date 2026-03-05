# Continuous Verification Runbook — P40

## Quick Commands

```bash
oc verify status      # Verification health overview
oc verify synthetic   # Run synthetic endpoint probes
oc verify canary      # Run canary function probes
oc verify gates       # Evaluate policy gates
oc verify tick        # Full pipeline
oc verify test        # Run acceptance tests
```

## Synthetic Checks

Probe real infrastructure endpoints to detect outages:
- **SSH checks**: Verify SSH connectivity to nova, mira, orin
- **DNS resolution**: Confirm DNS is working
- **Gateway ping**: Verify OPNsense reachability
- **Dashboard HTTP**: Confirm dashboard is serving

## Canary Checks

Lightweight function probes that validate core capabilities:
- **Disk canary**: Write/read/delete a temp file
- **DNS canary**: Query local DNS resolver

## Policy Gates

Enforce minimum thresholds before allowing operations:
- SLO error budget ≥ 10%
- Open incidents ≤ 3
- DR readiness score ≥ 60
- Security audit score ≥ 60

Gates return `ALLOW` or `BLOCK`. The gatekeeper subsystem uses gate status to approve/deny actions.

## History

All check results append to `artifacts/verification/history.jsonl` for trend analysis. Max size: 10MB with rotation.

## Integration

- Dashboard: Verification panel shows synthetic/canary/gate status
- Tick pipeline: runs as part of `oc verify tick` (recommended: every 5 minutes via cron)
- Gates feed into gatekeeper decision engine
