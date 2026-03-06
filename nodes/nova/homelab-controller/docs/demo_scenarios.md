# Demonstration Scenarios

Live failure simulations showing the full incident lifecycle:
**alert → incident → investigation → remediation artifact**

---

## Scenario 1: API Service Failure

**Trigger**: Platform API becomes unreachable

```bash
# Simulate via Alertmanager webhook
curl -X POST http://localhost:8081/events/alertmanager \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "alerts": [{
      "status": "firing",
      "labels": {"alertname": "API_Down", "severity": "critical", "instance": "10.1.1.21:8081"},
      "annotations": {"description": "Platform API health check failed"},
      "startsAt": "'$(date -u +%FT%TZ)'"
    }]
  }'
```

**Expected behavior**:
1. `incident.created` event emitted to event bus
2. Incident stored in `artifacts/recovery/incidents.json` with type `api_down`
3. Investigation via `POST /investigate` selects `api_down` playbook
4. Evidence gathered: health_check (failed), service_status (inactive)
5. Confidence: 0.95 (high) — both signals confirm failure
6. Policy engine: `restart_service` is low-risk, auto-apply at 0.95
7. Remediation artifacts generated: summary.md, proposal.json, patch-plan.md

**Verification**:
```bash
# Check incident
curl http://localhost:8081/incidents -H "Authorization: Bearer $TOKEN"

# Run investigation
curl -X POST http://localhost:8081/investigate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"service": "api", "simulate": true}'

# Generate remediation artifacts
curl -X POST http://localhost:8081/remediation/artifact \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"incident_id": "INC-..."}'
```

---

## Scenario 2: Node Unreachable

**Trigger**: Worker node stops responding to health checks

```bash
curl -X POST http://localhost:8081/events/alertmanager \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "alerts": [{
      "status": "firing",
      "labels": {"alertname": "Node_Unreachable", "severity": "warning", "instance": "10.1.1.22:9100"},
      "annotations": {"description": "Mira node not responding"},
      "startsAt": "'$(date -u +%FT%TZ)'"
    }]
  }'
```

**Expected behavior**:
1. Incident created with type `node_unreachable`
2. Investigation selects `node_unreachable` playbook
3. Evidence: ping_check (failed), ssh_check (simulated)
4. Confidence: 0.70-0.95 depending on signal count
5. Recommended action: `failover_service` (medium risk, requires review)

---

## Scenario 3: Configuration Drift

**Trigger**: Drift detection finds mismatch between desired and observed state

```bash
curl -X POST http://localhost:8081/events/alertmanager \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "alerts": [{
      "status": "firing",
      "labels": {"alertname": "Config_Drift", "severity": "warning", "instance": "nova"},
      "annotations": {"description": "SSH config drift detected on nova"},
      "startsAt": "'$(date -u +%FT%TZ)'"
    }]
  }'
```

**Expected behavior**:
1. Incident created with type `config_drift`
2. Investigation selects `config_drift` playbook
3. Evidence: drift_report, config_diff, recent_changes
4. Recommended action: `rollback_config` (medium risk, requires review)
5. Remediation artifact includes patch plan with rollback instructions

---

## Scenario 4: Token Compromise

**Trigger**: Suspicious authentication pattern detected

```bash
# 1. Create a token
python3 scripts/identity/token_issuer.py create viewer compromised-token

# 2. Revoke it immediately with reason
python3 scripts/identity/token_issuer.py revoke <token_id> --reason "suspected compromise"

# 3. Verify revoked token is rejected
curl -s http://localhost:8081/ -H "Authorization: Bearer <revoked_secret>"
# Returns 401

# 4. Check audit log
tail -5 artifacts/identity/api_audit.jsonl | python3 -m json.tool
```

**Expected behavior**:
1. Revoked token immediately returns 401 on any endpoint
2. Audit log shows `401_invalid` with source IP
3. `failed_auth_count` increments in platform status
4. Rate limiter blocks further attempts from same token

---

## Scenario 5: Recovery Engine Response

**Trigger**: Service health check fails, recovery engine activated

```bash
# Check service health
curl -X POST http://localhost:8081/recover \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"service": "api", "dry_run": true}'

# Attempt failover (dry run)
curl -X POST http://localhost:8081/failover \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"service": "api", "dry_run": true}'
```

**Expected behavior**:
1. Recovery engine checks `health_registry.json` for service definition
2. Health URL probed; failure triggers incident lifecycle
3. `recovery_policy.json` consulted for allowed actions
4. Dry-run mode: logs what would happen without executing
5. Live mode (requires `dry_run: false`): executes recovery action

---

## Full End-to-End Demo

Run the complete incident lifecycle:

```bash
# 1. Generate tokens
ADMIN=$(python3 scripts/identity/token_issuer.py create admin demo-admin 2>&1 | grep Secret | awk '{print $NF}')
AUTO=$(python3 scripts/identity/token_issuer.py create automation demo-auto 2>&1 | grep Secret | awk '{print $NF}')

# 2. Fire alert
curl -X POST http://localhost:8081/events/alertmanager \
  -H "Authorization: Bearer $AUTO" \
  -H "Content-Type: application/json" \
  -d '{"alerts":[{"status":"firing","labels":{"alertname":"API_Down","severity":"critical","instance":"10.1.1.21:8081"},"annotations":{"description":"API down"},"startsAt":"2026-03-06T00:00:00Z"}]}'

# 3. Investigate
curl -X POST http://localhost:8081/investigate \
  -H "Authorization: Bearer $ADMIN" \
  -H "Content-Type: application/json" \
  -d '{"service":"api","simulate":true}'

# 4. Generate remediation artifacts
curl -X POST http://localhost:8081/remediation/artifact \
  -H "Authorization: Bearer $ADMIN" \
  -H "Content-Type: application/json" \
  -d '{"incident_id":"INC-..."}'

# 5. Review artifacts
ls data/remediation/incidents/
cat data/remediation/incidents/INC-*-summary.md

# 6. Check event trail
python3 platform/events/bus.py list --limit 10
```
