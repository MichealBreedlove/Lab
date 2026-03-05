# Lab — Home Lab Infrastructure

Personal homelab running a multi-node AI + infrastructure cluster managed with OpenClaw, Ansible, and custom automation.

<!-- PORTFOLIO_START -->
## 🏗️ What This Lab Does

- **Local AI inference cluster** — 4 nodes running Ollama with Qwen 2.5 32B, DeepSeek Coder, LLaMA 3.1 70B
- **AI agent orchestration** — OpenClaw manages autonomous agents across all nodes
- **Infrastructure-as-code** — Ansible playbooks for config management and health checks
- **Self-healing automation** — SLO-driven actions, chaos testing, gatekeeper safety gates
- **Full SRE pipeline** — Snapshots → Evidence → Planning → Actions → SLOs → Incidents → Postmortems

## 📊 What It Demonstrates

- **Site Reliability Engineering** — SLOs, error budgets, burn rates, incident management
- **Infrastructure Automation** — Ansible, systemd, scheduled tasks, CI/CD
- **Security Practices** — Secret scanning, sanitization, credential policies, safety gates
- **AI/ML Operations** — Local LLM serving, model management, multi-node inference
- **Documentation Discipline** — Architecture docs, runbooks, postmortems, change logs

## 🔧 Priorities Built (P19–P29)

| Priority | Feature | Status |
|----------|---------|--------|
| P19 | Chaos Injection Framework | ✅ |
| P20 | Resilience Score + Regression Gate | ✅ |
| P21 | Planner (Goal Engine + What-If) | ✅ |
| P22 | Topology + Service Graph | ✅ |
| P23 | Action Executor + Approval Tiers | ✅ |
| P24 | Evidence Pack + Snapshot Diff | ✅ |
| P25 | Gatekeeper (Safety Gates) | ✅ |
| P26 | Change Management + Release Notes | ✅ |
| P27 | SLOs + Error Budget | ✅ |
| P28 | Incident Commander + Postmortems | ✅ |
| P29 | Portfolio Publisher (GitHub Pages) | ✅ |
<!-- PORTFOLIO_END -->

## Architecture

| Node | Role | OS | Hardware |
|------|------|----|----------|
| **Jasper** | Gateway / Windows workstation | Windows 11 | Gaming PC, RTX GPU |
| **Nova** | Ansible controller / AI node | Ubuntu | Linux server |
| **Mira** | AI compute node | Ubuntu | Linux server |
| **Orin** | AI compute node | Ubuntu | Linux server |

## Repo Structure

```
Lab/
├── docs/              # Architecture, runbooks, diagrams
├── inventory/         # Hardware, IP plan, services catalog
├── nodes/             # Per-node configs & state (segregated)
│   ├── jasper/        # Windows gateway
│   ├── nova/          # Controller + AI
│   ├── mira/          # AI compute
│   └── orin/          # AI compute
├── services/          # Cross-node service configs
│   ├── openclaw/      # Policies, priorities, artifacts
│   ├── ollama/        # LLM serving
│   ├── proxmox/       # Virtualization
│   └── truenas/       # Storage
├── snapshots/         # Daily/weekly infra snapshots
├── tools/             # Backup & automation scripts
└── .github/           # CI workflows (secret scanning, lint)
```

## Key Features

- **Automated backup**: Each node auto-commits sanitized state daily
- **Secret scanning**: GitHub Actions block any accidental credential commits
- **Segregated by node**: Each machine owns its own folder
- **Recruiter-friendly**: Clean documentation, architecture diagrams, runbooks

## Services

- **OpenClaw** — AI agent orchestration across all nodes
- **Ollama** — Local LLM inference (Qwen, DeepSeek, LLaMA)
- **Proxmox** — VM/container management
- **Ansible** — Configuration management from Nova

## Notes

- If OpenClaw runs as a system-level systemd service, enable linger so it remains active after logout:
  ```bash
  sudo loginctl enable-linger <username>
  ```
- `systemctl --user` output may be incomplete in non-login SSH sessions (DBUS unavailable). This is reported but does not fail runs.
- `ss -ltnp` shows PID/process only for processes owned by the SSH user. Add `become: yes` if root-level visibility is needed.

## License

Private infrastructure repo. Not for redistribution.
