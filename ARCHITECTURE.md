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
| OPNsense (6-port) | Firewall / Gateway / Router | 10.1.1.1 |
| Cisco Nexus 3064 | Core 40/10GbE switch | 10.1.1.200 |
| PROXMOX | Primary hypervisor (TrueNAS VM + Nova VM) | 10.1.1.2 |
| PROXMOX-2 | Secondary hypervisor (Mira VM + monitoring CT) | 10.1.1.4 |
| PROXMOX-3 | Tertiary hypervisor (Orin VM + Immich/Plex CTs) | 10.1.1.5 |
| TrueNAS SCALE | NAS / NFS storage (VM 200 on PROXMOX) | 10.1.1.11 |
| UniFi U7 Pro XG | Wireless AP | 10.1.1.19 |
| Immich | Photo management (CT 502 on Orin) | 10.1.1.30 |
| Plex | Media server (CT on Orin) | 10.1.1.31 |

## Network Fabric

### High-Speed Backbone (40/10GbE)

```
Jasper (RTX 4090 workstation)
  └── Mellanox ConnectX-3 Pro (2x QSFP+)
       └── LACP Port-Channel 10 (80 Gbps aggregate)
            └── Cisco Nexus 3064 (Eth1/49 + Eth1/50)

OPNsense firewall
  └── 4x 10GbE SFP+ (ix0–ix3)
       └── LACP Port-Channel 1 (30 Gbps active, 1 hot standby)
            └── Cisco Nexus 3064 (Eth1/1–Eth1/4)

Orin VM
  └── 10GbE SFP+ (ixgbe, allow_unsupported_sfp=1)
       └── Cisco Nexus 3064 (Eth1/47)

Mira VM (pending)
  └── BCM57810S dual SFP+ (ordered, not yet installed)
       └── Will connect to Nexus when arrives → VLAN 40/50 cutover
```

### Standard Access (1/2.5GbE)
- Nova, Mira (current): 1GbE via Nicgiga unmanaged switch → Nexus Eth1/48
- Jasper management: Intel I226-V 2.5GbE → 10.1.1.150

### VLAN Plan (pending Mira BCM57810S)
| VLAN | Name | Subnet |
|------|------|--------|
| 10 | MGMT | 10.1.10.0/24 |
| 20 | INFRA | 10.1.20.0/24 |
| 30 | STORAGE | 10.1.30.0/24 |
| 40 | AI | 10.1.40.0/24 |
| 50 | COMPUTE | 10.1.50.0/24 |
| 999 | BLACKHOLE | — |

### Shared Storage (NFS over 1GbE, upgrading to 10GbE)
- `10.1.1.11:/mnt/Tank/openclaw/agents` → `/mnt/openclaw` on all agent VMs
- `10.1.1.11:/mnt/Tank/openclaw/shared` → `/mnt/openclaw-shared` on all agent VMs
- Jasper: `Z:\` mapped to `\\TRUENAS\openclaw`

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
- Tagged releases: v1.0.0 (core platform), v1.1.0 (AI operations layer)

## Network Security

- All internal traffic on 10.1.1.0/24
- OPNsense firewall with static DHCP reservations
- UFW on all Linux nodes (SSH + service ports only, LAN-restricted)
- Platform API restricted to 10.1.1.0/24
- No public-facing services
