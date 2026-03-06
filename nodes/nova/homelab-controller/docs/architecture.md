# Platform Architecture

## Overview

The homelab control plane is a self-hosted reliability platform running on Nova (10.1.1.21) that manages a 3-node compute cluster plus Proxmox hypervisors and OPNsense firewall. It provides authenticated API access, automated incident response, AI-assisted investigation, and Git-backed remediation artifacts.

## System Diagram

```
                    +------------------+
                    |   Prometheus     |
                    |   :9090          |
                    +--------+---------+
                             |
                    +--------v---------+
                    |  Alertmanager    |
                    |  webhook         |
                    +--------+---------+
                             |
              +--------------v--------------+
              |     Platform API v2.2       |
              |     :8081                   |
              |  +------------------------+ |
              |  | Auth (Bearer/RBAC)     | |
              |  | Rate Limiter           | |
              |  | Route Dispatcher       | |
              |  +------------------------+ |
              +-+---+---+---+---+---+---+---+
                |   |   |   |   |   |   |
        +-------+   |   |   |   |   |   +--------+
        v           v   v   v   v   v             v
   Event Bus    Incidents  Recovery  AI Ops    Drift
   (JSONL)      (JSON)     Engine    Engine    Detection
                                |
                         +------+------+
                         v             v
                    Investigator   Remediator
                    (Playbooks)    (Artifacts)
                         |             |
                         v             v
                    Policy Engine  Git Branch
                    (Safety Gates) Suggestions
```

## Security Model

### Authentication
- All API endpoints require Bearer token authentication
- Tokens issued via `token_issuer.py` with `hlab_` prefix + SHA256 hash storage
- Default TTL: 168 hours (7 days)
- Revoked tokens immediately return 401

### Role-Based Access Control (RBAC)
- **viewer** (rank 0): Read-only access to status, topology, events, incidents
- **operator** (rank 1): Can trigger changes, snapshots, incidents
- **automation** (rank 1): Service account role for webhooks and scheduled tasks
- **sre** (rank 2): Can trigger investigations, remediation, chaos experiments, recovery
- **admin** (rank 3): Full access including failover and all write operations

### Network Security
- API bound to 10.1.1.0/24 subnet only
- TLS termination via Caddy reverse proxy (configured, manual install)
- UFW firewall rules restrict ports per service

### Service Accounts
- Non-interactive principals for automation
- Can be enabled/disabled independently of tokens
- Tracked separately in `data/auth/service_accounts.json`

## Identity and RBAC

```
Token Lifecycle:
  Create -> Active -> [Revoke] -> Rejected
                   -> [Expire] -> Rejected

Role Hierarchy:
  admin (3) > sre (2) > operator/automation (1) > viewer (0)

Endpoint Authorization:
  GET  /             -> viewer
  GET  /events       -> viewer
  POST /investigate  -> sre
  POST /recover      -> sre
  POST /failover     -> sre
  POST /events/alertmanager -> automation
```

## Incident Lifecycle

```
Alert Fired (Prometheus/Alertmanager)
  |
  v
POST /events/alertmanager
  |
  +-> Dedup check (alertname + instance)
  |     |
  |     +-> New: incident.created event
  |     +-> Existing: incident.updated event
  |
  v
Incident stored (artifacts/recovery/incidents.json)
  |
  v
POST /investigate (manual or automated trigger)
  |
  +-> Playbook selection (service + state match)
  +-> Evidence gathering (health, service status, audit)
  +-> Confidence scoring (multi-signal rules)
  +-> Policy evaluation (risk level + role + threshold)
  |
  v
Investigation artifact (data/incidents/investigations/INV-*.json)
  |
  v
POST /remediation/artifact
  |
  +-> Summary markdown (INC-*-summary.md)
  +-> Proposal JSON (INC-*-proposal.json)
  +-> Patch plan markdown (INC-*-patch-plan.md)
  +-> Git branch suggestion
  |
  v
Human review or auto-apply (policy-gated)
```

## AI Investigation Flow

1. **Trigger**: POST /investigate with incident_id and service name
2. **Playbook Selection**: Match service + state against `platform/incidents/playbooks/*.json`
3. **Evidence Gathering**: Execute playbook steps (health_check, service_status, ping_check, etc.)
4. **Confidence Scoring**: Apply multi-signal rules from playbook `confidence_rules`
5. **Policy Evaluation**: `policy_engine.py` determines auto_apply / require_review / deny_execution
6. **Enrichment**: Add blast_radius, reversible, policy_decision to investigation
7. **Persist**: Write to `data/incidents/investigations/INV-*.json`
8. **Events**: Emit `ai.investigation.started` and `ai.investigation.completed`

### Playbooks
- `api_down.json` — API service failure investigation
- `node_unreachable.json` — Node connectivity investigation
- `config_drift.json` — Configuration drift investigation

## Remediation Artifact System

Generates Git-friendly incident documentation:
- **Summary** (`INC-*-summary.md`): Human-readable incident overview
- **Proposal** (`INC-*-proposal.json`): Machine-readable remediation plan
- **Patch Plan** (`INC-*-patch-plan.md`): Step-by-step execution and rollback guide
- **Git Metadata**: Suggested branch name and commit message

## Recovery Engine

- Health checks via `health_registry.json` service definitions
- Recovery actions defined in `recovery_policy.json`
- Failover mappings in `failover_map.json`
- Dry-run by default; explicit flag required for live execution
- Incident tracking in `artifacts/recovery/incidents.json`

## Event Bus Architecture

- **Storage**: Append-only JSONL at `data/events/event_log.jsonl`
- **Event Types**: 10 types covering incidents, recovery, AI investigation, remediation
- **Query API**: GET /events with type, incident_id, limit filters
- **Producers**: Recovery engine, investigator, remediator, policy engine, alert ingest
- **Crash Safety**: Append-only write; no state to corrupt on restart

## Execution Policy

- **Low risk** (restart_service): Auto-apply at confidence >= 0.90
- **Medium risk** (rollback_config, failover_service): Requires review + role authorization
- **High risk** (firewall_change, delete_data): Always requires human approval
- Audit trail in `artifacts/identity/policy_audit.jsonl`
