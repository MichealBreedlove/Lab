# Lab — Home Lab Infrastructure

Personal homelab running a multi-node AI + infrastructure cluster managed with OpenClaw, Ansible, and custom automation.

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
