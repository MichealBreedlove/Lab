# Lab — AI Infrastructure & Homelab

Multi-node infrastructure cluster running AI inference, SRE automation, and security tooling. Managed with OpenClaw, Ansible, and custom Python/Bash automation.

Part of the infrastructure documented at [michealbreedlove.com](https://michealbreedlove.com).

---

## Architecture

| Node | Role | Hardware | OS |
|---|---|---|---|
| **Jasper** | GPU inference, gateway, dev workstation | i9-13900K, RTX 4090, 64 GB | Windows 11 Pro |
| **Nova** | Ansible controller, storage, services | Intel N305, 32 GB DDR5 | Ubuntu (Proxmox) |
| **Mira** | Utility compute | i7-2600K, 16 GB | Ubuntu (Proxmox) |
| **Orin** | Server workloads | Dual Xeon E5-2667v4, 16 GB ECC | Ubuntu (Proxmox) |

**Network:** 2.5 GbE + 10 GbE segments, OPNsense firewall, UniFi AP, VLAN segmentation

---

## What This Lab Demonstrates

**Site Reliability Engineering**
SLO evaluation with error budgets, burn-rate alerting across 5 time windows, incident tracking, auto-generated postmortems, and safety gates that block risky automation when reliability is degraded.

**Infrastructure Automation**
Ansible playbooks for provisioning and config management, systemd services, scheduled backup tasks, and CI/CD pipelines with GitHub Actions.

**Security Practices**
Secret scanning (11 regex patterns), credential sanitization on every commit, VLAN segmentation, least-privilege access, and automated restore verification.

**AI/ML Operations**
Local LLM inference via Ollama (RTX 4090), multi-model orchestration through OpenClaw, distributed agent execution across all nodes.

---

## Key Systems

| System | Purpose |
|---|---|
| OpenClaw | AI agent orchestration across all nodes |
| Ollama | Local LLM inference (GPU-backed on Jasper) |
| Proxmox | VM and container management (3-node cluster) |
| Ansible | Configuration management from Nova |
| TrueNAS | Network storage |
| OPNsense | Firewall, routing, VLAN management |

---

## Reliability Pipeline

End-to-end SRE automation running on Nova:

1. **SLO Evaluation** — 6 service-level objectives across 5 sliding windows
2. **Burn-Rate Alerting** — Detects budget consumption trends before breach
3. **Incident Management** — Automated detection, tracking, and escalation
4. **Postmortems** — Auto-generated with timeline, root cause, and action items
5. **Safety Gates** — Block automation when error budget is exhausted
6. **Acceptance Tests** — 38+ tests validate every pipeline component

→ [Case study: SRE Pipeline](https://michealbreedlove.com/case-study-sre-pipeline.html)

---

## GitOps & Backup System

Automated daily backups from all 4 nodes with CI enforcement:

- Per-node sanitized state committed daily
- GitHub Actions CI gate scans for 11 secret patterns
- Restore verification and node rebuild documentation
- Zero credential leaks since deployment

→ [Case study: GitOps Backups](https://michealbreedlove.com/case-study-gitops-backups.html)

---

## Repo Structure

```
Lab/
├── docs/              # Architecture docs, runbooks
├── inventory/         # Hardware specs, IP plan, services catalog
├── nodes/             # Per-node configs and state (segregated)
│   ├── jasper/        # Windows gateway + GPU inference
│   ├── nova/          # Controller + homelab-controller system
│   ├── mira/          # Utility compute
│   └── orin/          # Server workloads
├── services/          # Cross-node service configs
├── site/              # MkDocs documentation site
├── snapshots/         # Daily/weekly infrastructure snapshots
├── tools/             # Backup and automation scripts
└── .github/           # CI workflows (secret scanning)
```

---

## Security Considerations

- All commits pass CI secret scanning before merge
- Credentials stored outside the repo; policy documented in `inventory/creds_policy.md`
- VLAN segmentation isolates IoT, infrastructure, and personal devices
- SSH key authentication only; no password-based access
- Sensitive values redacted in all public-facing documentation

---

## Links

- [Portfolio](https://michealbreedlove.com)
- [AI Cluster Architecture](https://michealbreedlove.com/ai-cluster.html)
- [Proof Pack](https://michealbreedlove.com/proof.html)
