# Bootstrap Runbook — Zero-Touch Node Bootstrap (P31)

## Overview

Bootstrap a new or recovering node into the OpenClaw cluster with a single command. The system handles dependency installation, OpenClaw pairing, service configuration, timer setup, topology registration, and validation.

## Prerequisites

- SSH key auth configured (`~/.ssh/id_ed25519`)
- Target node reachable on the network
- Node defined in `config/node_profiles.json`
- Bootstrap policy enabled in `config/bootstrap_policy.json`

## Quick Start

```bash
# Preflight check (non-destructive)
oc bootstrap validate --node nova

# Full bootstrap — dry run (shows plan, doesn't execute)
oc bootstrap node nova

# Full bootstrap — apply (executes all steps)
oc bootstrap node nova --apply

# Check all nodes
oc bootstrap status

# Run acceptance tests
oc bootstrap test
```

## Architecture

### Node Profiles

Three profiles defined in `config/node_profiles.json`:

| Profile | Description | Nodes |
|---------|-------------|-------|
| `controller` | SRE automation, storage, Ansible | nova |
| `worker` | Compute agent execution | mira, orin |
| `gpu` | GPU inference, gateway | jasper (Windows) |

### Pipeline Stages

1. **Preflight** (`bootstrap_preflight.py`) — Verify network, SSH, ports, policy
2. **Install** (`bootstrap_install.py`) — apt packages, pip deps, repo clone, OpenClaw
3. **Configure** (`bootstrap_configure.py`) — OpenClaw pairing, timers, node configs
4. **Register** (`bootstrap_register.py`) — Topology, services catalog, IP plan
5. **Validate** (`bootstrap_validate.py`) — End-to-end health checks

### Orchestrator

`bootstrap_tick.sh <node> [--apply]` runs all stages in sequence. Without `--apply`, only preflight + dry-run install are executed.

## Node-Specific Notes

### Linux Nodes (Nova, Mira, Orin)

- Full pipeline supported
- SSH key auth required
- systemd user services for OpenClaw + timers
- Linger enabled for user service persistence

### Windows Nodes (Jasper)

- Use `bootstrap_windows.ps1` for gateway-side checks
- Manual pairing may be required
- No systemd — uses Windows Scheduled Tasks

## Artifacts

All stages write JSON artifacts to `artifacts/bootstrap/`:

- `preflight_<node>.json` — Preflight results
- `install_<node>.json` — Install step outcomes
- `configure_<node>.json` — Configuration results
- `register_<node>.json` — Registration actions
- `validate_<node>.json` — Validation checks + summary

## Portfolio Export

```bash
python3 scripts/bootstrap/bootstrap_export_portfolio.py --lab-repo /path/to/Lab
```

Exports sanitized bootstrap artifacts to `Lab/exports/bootstrap/`. All tokens, passwords, and private keys are automatically redacted.

## Troubleshooting

### Preflight fails: SSH check

```bash
# Verify SSH connectivity manually
ssh -i ~/.ssh/id_ed25519 micheal@10.1.1.22 echo ok

# Check SSH key permissions
chmod 600 ~/.ssh/id_ed25519
```

### Install fails: package not found

```bash
# SSH to node and update apt cache manually
ssh micheal@<ip> "sudo apt-get update"
```

### Validate fails: OpenClaw port not listening

```bash
# Check if OpenClaw is running on the node
ssh micheal@<ip> "systemctl --user status openclaw-node"

# Restart if needed
ssh micheal@<ip> "systemctl --user restart openclaw-node"
```

## Safety

- **Dry-run is default** — `--apply` must be explicitly passed
- **Idempotent** — safe to run multiple times
- **No destructive actions** — installs and configures, never removes
- **Secret scan** — portfolio export runs pattern matching before writing
