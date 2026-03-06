# Distributed AI Cluster Architecture

## Overview

The OpenClaw cluster operates as a distributed AI SRE team where each node runs a specialized agent. Work flows through a structured task bus with policy-gated execution, capability-based routing, and automatic failover.

## System Diagram

```
                   +------------------+
                   |  JASPER          |
                   |  Coordinator     |
                   |  10.1.1.150      |
                   +--------+---------+
                            |
              +-------------+-------------+
              |             |             |
     +--------+--+  +------+----+  +-----+------+
     |   NOVA    |  |   MIRA    |  |   ORIN     |
     |  Proxmox  |  |  Network  |  |   Heavy    |
     | Optimizer |  | Optimizer |  | Analysis   |
     | 10.1.1.21 |  | 10.1.1.22 |  | 10.1.1.23 |
     +-----------+  +-----------+  +------------+
```

## Components

### Agent Registry (P64)
Live tracking of all agents: ID, role, capabilities, status, heartbeat, execution mode.

### Task Bus (P65)
Structured task queue: create → route → claim → execute → complete. JSONL-backed.

### Capability Router (P66)
Routes tasks to the best agent by role, capability, health, and fallback chain.

### Node Agents (P67)
Each node runs a specialized runtime (base_agent.py subclass) that registers, heartbeats, polls tasks, executes within capability bounds, and returns structured results.

### Health Monitor (P68)
Tracks heartbeats. Marks agents degraded (90s) then offline (180s). Auto-reassigns low-risk tasks. Never auto-reassigns high-risk tasks.

### Execution Policy (P69)
Gates every task execution by agent role, capability, execution mode, and risk level. Audit-mode agents can only run audits. Autonomous agents get a broader but still bounded set.

### Artifact Handoff (P70)
Enables multi-agent workflows where one agent's output becomes another's input. Supports workflow composition with dependency chains.

### Scheduled Operations (P71)
Recurring task scheduler with interval tracking. Generates daily scorecards.

## Task Flow

```
1. Scheduler creates task (or API creates task)
2. Router selects target agent by capability/role/health
3. Agent claims task from bus
4. Execution policy evaluates: allow / deny / require_review
5. Agent executes task handler
6. Agent returns structured result
7. Result stored; handoff created if workflow continues
8. Events emitted at each step
```

## Safety Properties

- Agents can only execute tasks matching their capabilities
- Execution mode restricts what task types are allowed
- High-risk tasks are never auto-reassigned on failover
- Infrastructure changes follow the existing safety model
- All actions audited via event bus
