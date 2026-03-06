# Distributed Cluster Demo Scenarios

## Scenario 1: Multi-Agent Firewall Audit

```
Scheduler -> creates audit_firewall task
Router -> routes to Mira
Mira -> claims task, runs firewall_optimizer.run_audit()
Mira -> returns structured result (findings, confidence)
Mira -> creates handoff artifact for Jasper
Jasper -> consumes handoff, generates summary artifact
```

## Scenario 2: Incident Response Pipeline

```
Alertmanager -> POST /events/alertmanager (API_Down alert)
Platform -> creates incident
Jasper -> creates investigate_incident task
Router -> routes to Orin (heavy_analysis)
Orin -> runs investigation, returns findings
Orin -> creates handoff for Jasper
Jasper -> reviews, generates remediation artifact
```

## Scenario 3: Node Failure and Failover

```
Mira stops sending heartbeats
Health monitor -> marks Mira degraded (90s)
Health monitor -> marks Mira offline (180s)
Queued audit_firewall task -> reassigned to Jasper (fallback)
Mira recovers -> sends heartbeat -> marked online
Future firewall tasks -> route back to Mira
```

## Scenario 4: Proxmox Hygiene Scan

```
Scheduler -> creates audit_proxmox task
Router -> routes to Nova
Nova -> runs cluster_optimizer.run_audit()
Nova -> detects: 2 missing tags, 1 orphaned snapshot
Nova -> returns result with requires_review=true
Jasper -> reviews findings in daily scorecard
```

## Scenario 5: Policy-Denied Execution

```
Task created: investigate_incident for Mira
Execution policy evaluates: Mira is in audit mode
Execution policy -> DENY (investigate not allowed in audit mode)
Task remains queued
Router -> reassigns to Jasper or Orin (assisted mode)
```

## Running Demos

```bash
# Register all agents
python3 platform/agents/jasper_agent.py &  # or run_once()
python3 platform/agents/nova_agent.py &
python3 platform/agents/mira_agent.py &
python3 platform/agents/orin_agent.py &

# Create a task
python3 platform/cluster/task_bus.py create audit_firewall jasper network_optimizer

# Run scheduler
python3 platform/cluster/scheduler.py tick

# Generate scorecard
python3 platform/cluster/scheduler.py scorecard

# Check health
python3 platform/cluster/health.py check
```
