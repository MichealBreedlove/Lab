# Cluster Safety Model

## Core Rule

The distributed cluster must NEVER perform actions that could lock the operator out or destroy infrastructure state.

## Safety Layers

### Layer 1: Capability Enforcement
Agents can only execute tasks matching their registered capabilities. A network agent cannot modify Proxmox configs.

### Layer 2: Execution Mode
- **audit**: observe-only tasks
- **assisted**: observe + generate recommendations (human applies)
- **autonomous_low_risk**: observe + apply only pre-approved low-risk actions

### Layer 3: Task Routing Policy
Tasks are routed to the correct agent. Unknown tasks default to Jasper (coordinator) for review.

### Layer 4: Execution Policy Evaluation
Every task is evaluated before execution: allow / deny / require_review. Denied tasks are never executed.

### Layer 5: Health-Gated Failover
- Offline agents cannot receive tasks
- Low-risk tasks may be reassigned to fallback agents
- High-risk tasks are NEVER auto-reassigned
- Risky actions are never silently delegated to a fallback node

### Layer 6: Infrastructure Safety Model
All existing infrastructure safety rules apply:
- Firewall: WAN rules, gateway, DHCP, DNS, VLANs never auto-modified
- WiFi: SSID, security mode, controller never auto-modified
- Proxmox: bridges, bonds, VLANs, storage, HA, quorum never auto-modified

### Layer 7: Audit Trail
Every action logged via:
- Event bus (JSONL)
- Task bus (task lifecycle)
- Policy audit log
- Agent heartbeat log

## Failure Modes

| Failure | System Response |
|---------|----------------|
| Agent crashes | Heartbeat timeout → degraded → offline |
| Agent offline | Tasks rerouted to fallback (low-risk only) |
| All agents offline | Tasks queue until recovery; no auto-execution |
| Policy disabled | All task execution denied |
| Network partition | Agents degrade gracefully; no split-brain execution |
