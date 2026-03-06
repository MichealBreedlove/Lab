# Identity + Access Layer

## Overview

The identity layer provides role-based access control, token management, session logging, and audit trails for the homelab control plane.

## Roles

| Role | Description | Access Level |
|------|-------------|-------------|
| **admin** | Full control plane access | All actions |
| **operator** | Run commands, trigger changes | Most operational actions |
| **viewer** | Read-only status access | Status and list commands only |
| **automation** | Scheduled tasks and CI | Drift, snapshots, validation |

## Token Management

Tokens are the primary authentication mechanism. Each token:
- Has a unique ID prefixed with `hlab_`
- Is bound to a role
- Has a configurable TTL (default: 168 hours / 7 days)
- Is stored as a SHA-256 hash (raw secret shown only at creation)

### Commands

```bash
oc auth token create <role> <name>   # Create new token
oc auth token revoke <token_id>      # Revoke a token
oc auth token list                   # List active tokens
oc auth token list --all             # Include expired/revoked
```

### Token Lifecycle

1. **Create** — Generates token, stores hash, returns secret once
2. **Use** — Token validated on each request, `last_used` updated
3. **Expire** — Token rejected after TTL
4. **Revoke** — Token immediately invalidated
5. **Cleanup** — Expired tokens purged after retention period

## Network Security

Access is restricted to trusted subnets defined in `config/identity_policy.json`:
- `10.1.1.0/24` (LAN)
- `127.0.0.0/8` (loopback)

Requests from outside these subnets are rejected before token validation.

## Audit Trail

Every authorization check produces an audit event:

```json
{
  "timestamp": "2026-03-06T...",
  "event_type": "auth_granted",
  "actor": "operator-token",
  "target": "drift:run",
  "result": "success"
}
```

Audit logs are stored as daily JSONL files in `artifacts/identity/audit/`.

## Session Logging

All commands are logged with:
- Timestamp
- User / token ID
- Command executed
- Target component
- Result (granted/denied/error)
- Source IP

Session logs: `artifacts/identity/sessions/`

## Break-Glass

Emergency access mechanism:
- Generates a time-limited token (30 min)
- Requires admin role
- All usage is audit-logged
- Token stored at `config/break_glass.token` (never committed)

## Dashboard

The identity panel shows:
- Active tokens count
- Last audit event
- Failed auth count
- Break-glass state

Data: `dashboard/static/data/identity_status.json`

## Files

| File | Purpose |
|------|---------|
| `config/identity_policy.json` | Role definitions, token config, subnets |
| `scripts/identity/token_issuer.py` | Token CRUD operations |
| `scripts/identity/auth_manager.py` | Authorization checks |
| `scripts/identity/session_logger.py` | Command session logging |
| `scripts/identity/audit_log.py` | Structured audit events |
| `scripts/identity/identity_tick.sh` | Periodic cleanup + export |
| `artifacts/identity/active_tokens.json` | Token store |
| `artifacts/identity/audit/` | Daily audit logs (JSONL) |
| `artifacts/identity/sessions/` | Daily session logs (JSONL) |
