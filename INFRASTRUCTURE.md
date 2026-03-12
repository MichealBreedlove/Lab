# Infrastructure

Complete host and network inventory for the homelab cluster.

---

## Host Inventory

| Host | IP | Role |
|---|---|---|
| **OPNsense** | 10.1.1.1 | Gateway / Firewall / Router |
| **PROXMOX** | 10.1.1.2 | Primary Proxmox hypervisor |
| **PROXMOX-SFP** | 10.1.1.3 | Proxmox node (SFP+) |
| **PROXMOX-2** | 10.1.1.4 | Second Proxmox node |
| **PROXMOX-3** | 10.1.1.5 | Third Proxmox node (Dell R-series, iDRAC: 10.1.1.220) |
| **TrueNAS** | 10.1.1.11 | NAS — VM 200 on PROXMOX, 10G SFP+ via vmbr1 |
| **Jasper** (GamingPC) | 10.1.1.150 / .151 | Orchestrator — i9-13900K, 64 GB, RTX 4090 |
| **Nova** | 10.1.1.21 | AI Agent Node — VM 201 on PROXMOX (64 GB disk) |
| **Mira** | 10.1.1.22 | AI Agent Node |
| **Orin** | 10.1.1.23 | AI Agent Node (heavy analysis) |
| **UniFi Controller** | 10.1.1.100 | CT 300 on PROXMOX-2 |
| **UniFi AP** | 10.1.1.19 | U7-Pro-XG-B |
| **Plex** | 10.1.1.31 | Media Server |
| **Immich** | 10.1.1.30 | Photo Management |
| **Monitoring** | 10.1.1.25 | Grafana + Prometheus |
| **Nexus 3000** | 10.1.1.200 | Core switch |

---

## Network Fabric

### High-Speed Backbone (40/10 GbE)

```
Jasper (RTX 4090 workstation)
  └── Mellanox ConnectX-3 Pro (2x QSFP+)
       └── LACP Port-Channel 10 (80 Gbps aggregate)
            └── Cisco Nexus 3000 (core switch)

OPNsense firewall
  └── 4x 10 GbE SFP+ (ix0–ix3)
       └── LACP Port-Channel 1 (30 Gbps active, 1 hot standby)
            └── Cisco Nexus 3000

TrueNAS (VM 200 on PROXMOX)
  └── 10G SFP+ via vmbr1
       └── Cisco Nexus 3000
```

### Standard Access (1 GbE)

All remaining hosts connect at 1 GbE to the Nexus 3000.

### Wireless

UniFi U7-Pro-XG-B (10.1.1.19) managed by UniFi Controller (CT 300 on PROXMOX-2, 10.1.1.100).

---

## VLAN Segmentation

Managed by OPNsense. VLANs enforce isolation between management, AI agent, storage, and media traffic. See ARCHITECTURE.md for fabric detail.

---

## Proxmox Cluster

| Node | IP | Notable Guests |
|---|---|---|
| PROXMOX | 10.1.1.2 | TrueNAS (VM 200), Nova (VM 201) |
| PROXMOX-SFP | 10.1.1.3 | SFP+ uplink node |
| PROXMOX-2 | 10.1.1.4 | UniFi Controller (CT 300) |
| PROXMOX-3 | 10.1.1.5 | Plex, Immich; iDRAC at 10.1.1.220 |

---

## Related Docs

- [ARCHITECTURE.md](ARCHITECTURE.md) — network fabric diagrams, LACP config, VLAN layout
- [OBSERVABILITY.md](OBSERVABILITY.md) — Prometheus targets, Grafana dashboards, alerting
- [OPERATIONS.md](OPERATIONS.md) — runbooks, maintenance procedures
- [docs/tools.md](docs/tools.md) — automation tooling (memsearch, TruffleHog, morning brief)
