# Latest Reliability Demo

**Generated:** 2026-03-06T02:07:57.026496+00:00
**Scenario:** gateway_restart_outage

## Results

- **Failure detected:** Yes (simulated)
- **Remediation ran:** Yes (simulated gateway restart)
- **Validation passed:** Yes
- **Change log entry:** `none`
- **Evidence pack:** Empty (simulation mode)
- **Postmortem stub:** Generated inline

## Artifact Locations

- Change log: `changes/CHG-20260306-020814-ba00be/`
- Demo artifacts: `artifacts/demos/`
- Validation: `changes/CHG-20260306-020814-ba00be/validation.json`

## Scenario Description

Simulates an OpenClaw gateway outage. The platform:
1. Establishes baseline connectivity
2. Injects simulated failure (gateway process marked unreachable)
3. Detects the anomaly via health checks
4. Executes remediation (restart simulation)
5. Validates recovery (all endpoints responsive)
6. Generates evidence pack with timestamps and logs

---
*This demo runs in simulation mode -- no actual services are disrupted.*
