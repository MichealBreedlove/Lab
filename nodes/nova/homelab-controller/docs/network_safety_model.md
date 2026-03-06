# Network Safety Model

## Core Principle

The platform must NEVER perform actions that could lock the operator out of the network or destroy infrastructure state.

## Safety Hierarchy

```
DENY (always blocked)
  |-- WAN rule modifications
  |-- Default deny rule changes
  |-- Gateway/routing changes
  |-- VLAN trunk modifications
  |-- Management access rule changes
  |-- Cluster quorum changes
  |-- SSID/security mode changes
  |
REVIEW (require human approval)
  |-- DHCP configuration changes
  |-- DNS resolver changes
  |-- Firewall rule reordering
  |-- Storage migration
  |-- HA policy changes
  |-- Bridge/bond changes
  |
ASSISTED (generate + wait for approval)
  |-- Rule cleanup suggestions
  |-- Alias normalization
  |-- Channel reassignment
  |-- Power adjustment
  |-- Backup schedule fixes
  |
AUTO (low-risk, policy-gated)
  |-- Tag standardization
  |-- Documentation notes
  |-- Metadata normalization
  |-- Template flagging
  |-- Config snapshots
```

## Change Lifecycle

```
observe -> analyze -> propose -> simulate -> backup -> apply -> validate -> rollback
                                                         |
                                                    (if validation fails)
```

### Pre-Change Checklist
1. Current config backed up to `data/network_audit/` or `data/proxmox_audit/`
2. Baseline connectivity verified (all nodes reachable)
3. Change proposal generated with rollback plan
4. Policy engine evaluates risk level
5. Human approval obtained (if required)

### Post-Change Validation
1. All management interfaces reachable
2. SSH access to all nodes confirmed
3. API endpoints responding
4. No new incidents triggered
5. Dashboard status unchanged or improved

### Automatic Rollback Triggers
- Management interface unreachable after change
- SSH connectivity lost to any node
- API health check fails
- Validation timeout exceeded (60 seconds)

## Audit Trail

All infrastructure optimization actions are logged:
- `data/network_audit/*.json` — firewall and WiFi reports
- `data/proxmox_audit/*.json` — cluster audit reports
- `data/events/event_log.jsonl` — event bus entries
- `artifacts/identity/policy_audit.jsonl` — policy decisions

## Mode Transitions

Modes can only be changed via config file edits (never via API):

```json
// config/network_optimizer.json
{"mode": "audit"}        // default — observe only
{"mode": "assisted"}     // generate suggestions
{"mode": "autonomous"}   // auto-apply low-risk only

// config/proxmox_optimizer.json
{"mode": "audit"}        // default
{"mode": "autonomous_low_risk"}  // auto-apply tags/notes only
```

WiFi is always `assisted` mode — no autonomous option.
