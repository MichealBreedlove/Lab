# Network Architecture

## Subnet: 10.1.1.0/24

| Node | IP | Role |
|------|----|------|
| Jasper | 10.1.1.x | Gateway / Windows workstation |
| Nova | 10.1.1.21 | Ansible controller / AI node |
| Mira | 10.1.1.22 | AI compute node |
| Orin | 10.1.1.23 | AI compute node |

## Key Ports
- **18789** — OpenClaw gateway
- **18793** — OpenClaw node
- **11434** — Ollama API
- **8006** — Proxmox web UI (if applicable)

## SSH
- Key: `~/.ssh/id_ed25519_homelab`
- Controller: Nova
- Managed: Mira, Orin
