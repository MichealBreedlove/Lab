# Architecture

## Overview

This homelab operates as a production-grade infrastructure platform built to demonstrate enterprise security, reliability, and operations practices at portfolio scale.

## Nodes

| Node | Role | Hardware | IP |
|------|------|----------|----|
| **Jasper** (GamingPC) | Gateway + Operator Console | i9-13900K, RTX 4090, 64GB DDR5 | 10.1.1.150 |
| **Nova** | Control Plane + Controller | Intel N305, 32GB DDR5 | 10.1.1.21 |
| **Mira** | Compute Worker | i7-2600K, 16GB DDR3 | 10.1.1.22 |
| **Orin** | Compute Worker | Dell R630, Dual Xeon E5-2667v4, 16GB ECC | 10.1.1.23 |

### Jasper (Gateway)

Runs the OpenClaw AI gateway, Ollama inference (RTX 4090), and serves as the operator console. Windows 11 Pro. All GitHub pushes originate here.

### Nova (Control Plane)

Single management node for the entire infrastructure. Runs:
- Homelab controller (drift detection, change logs, evidence packs)
- Platform API (HTTP control interface on port 8081)
- Observability stack (Prometheus, Grafana, Loki on Docker)
- Dashboard (port 8080)
- Ansible playbooks for inventory collection
- Systemd timers for automated ticks

### Mira + Orin (Workers)

Compute nodes managed by Nova via SSH. Run OpenClaw worker agents. Monitored by Prometheus node_exporter.

## Infrastructure

| Device | Role | IP |
|--------|------|----|
| OPNsense | Firewall / Gateway | 10.1.1.1 |
| PROXMOX (×3) | Virtualization Cluster | 10.1.1.2, .4, .5 |
| TrueNAS | Storage (NFS) | 10.1.1.200 |
| UniFi U7 Pro XG | Wireless AP | 10.1.1.19 |

## Control Plane Architecture

Nova owns the control plane with these subsystems:

- **Drift Detection** — Desired state configs compared against live SSH-collected state. GREEN/YELLOW/RED status.
- **Change Log + Evidence Packs** — Every infrastructure change produces a unique `CHG-*` record with diff, validation, and evidence.
- **Platform API** — Internal HTTP API (port 8081) for triggering changes, chaos tests, snapshots, and incidents.
- **Observability** — Prometheus scrapes node metrics; Grafana dashboards; Loki aggregates logs via Promtail.
- **Reliability Demos** — Scripted chaos scenarios with baseline → inject → detect → remediate → validate phases.
- **Inventory Collection** — Ansible playbooks collect configs from OPNsense, Proxmox, and all nodes on schedule.
- **Security Hygiene** — Secret scanning, supply chain verification, and hardening audits run as part of the release process.

## GitHub Strategy

- **Primary repo:** `MichealBreedlove/Lab` — per-node segregation, all automation, docs, and artifacts
- **Portfolio repos:** Separate repos for SRE pipeline, GitOps backups, security toolkit, starter template
- All pushes go through GamingPC (Nova has no GitHub credentials)
- Secrets never committed; secret scanner runs before every push
- Tagged releases: v1.0.0 (P1-P35), v1.1.0 (P36-P42)

## Network Security

- All internal traffic on 10.1.1.0/24
- OPNsense firewall with static DHCP reservations
- UFW on all Linux nodes (SSH + service ports only, LAN-restricted)
- Platform API restricted to 10.1.1.0/24
- No public-facing services
