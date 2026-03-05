# Home Lab Overview

## Purpose
Multi-node AI inference and infrastructure automation cluster for:
- Local LLM serving (Ollama — Qwen, DeepSeek, LLaMA)
- AI agent orchestration (OpenClaw)
- Infrastructure-as-code (Ansible from Nova)
- Self-healing, self-monitoring automation pipeline

## Nodes
- **Jasper** (Windows 11) — Gateway, OpenClaw main agent, workstation
- **Nova** (Ubuntu) — Ansible controller, AI compute, cluster brain
- **Mira** (Ubuntu) — AI compute, OpenClaw node
- **Orin** (Ubuntu) — AI compute, OpenClaw node

## Network
- All nodes on 10.1.1.x subnet
- SSH key-based auth between Linux nodes
- OpenClaw pairing for orchestration

## Automation Stack
- OpenClaw: agent-based orchestration
- Ansible: config management + health checks
- systemd: service management (system-level)
- GitHub: backup + audit trail
