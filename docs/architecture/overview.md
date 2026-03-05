# Architecture Overview

4-node cluster providing AI inference, SRE automation, and infrastructure services.

## Topology

```
                    ┌─────────────┐
                    │  OPNsense   │
                    │  (Gateway)  │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼─────┐ ┌───▼───┐ ┌─────▼─────┐
        │  Jasper   │ │  Nova │ │   Orin    │
        │  (GPU)    │ │ (Ctrl)│ │  (Server) │
        └───────────┘ └───┬───┘ └───────────┘
                          │
                    ┌─────▼─────┐
                    │   Mira    │
                    │ (Compute) │
                    └───────────┘
```

## Node Roles

| Node | Primary Role | Secondary Role |
|---|---|---|
| Jasper | GPU inference (RTX 4090) | Gateway, dev workstation |
| Nova | Ansible controller | Storage, SRE automation |
| Mira | Utility compute | Agent execution |
| Orin | Server workloads | Agent execution |

## Network

- **Backbone:** 2.5 GbE with 10 GbE links for storage traffic
- **Firewall:** OPNsense on Qotom Q20342G9
- **WiFi:** UniFi U7 Pro XG AP
- **Segmentation:** VLANs for infrastructure, IoT, personal devices

## Key Services

- OpenClaw — AI agent orchestration
- Ollama — Local LLM inference
- Proxmox — Virtualization (3-node cluster)
- Ansible — Configuration management
- TrueNAS — Network storage
