# Hardware Inventory

## Nodes

### Jasper (Primary)

- **CPU:** Intel i9-13900K (24 cores / 32 threads)
- **GPU:** NVIDIA RTX 4090 (24 GB VRAM)
- **RAM:** 64 GB DDR5
- **Storage:** 1.8 TB NVMe (OS) + 4× ~20 TB drives
- **OS:** Windows 11 Pro
- **Network:** 2.5 GbE
- **Role:** GPU inference, OpenClaw gateway, development

### Nova (Controller)

- **CPU:** Intel N305 (8 cores)
- **RAM:** 32 GB DDR5
- **Storage:** 24 TB HDD
- **OS:** Ubuntu (Proxmox)
- **Network:** 2.5 GbE
- **Role:** Ansible controller, storage, SRE automation

### Mira (Compute)

- **CPU:** Intel i7-2600K (4 cores / 8 threads)
- **RAM:** 16 GB DDR3
- **OS:** Ubuntu (Proxmox)
- **Network:** 1 GbE
- **Role:** Utility compute, agent execution

### Orin (Server)

- **CPU:** Dual Intel Xeon E5-2667v4 (16 cores / 32 threads)
- **RAM:** 16 GB DDR4 ECC
- **Chassis:** Dell PowerEdge R630
- **OS:** Ubuntu (Proxmox)
- **Network:** 10 GbE
- **Role:** Server workloads, agent execution

## Infrastructure

| Device | Role | IP |
|---|---|---|
| OPNsense (Qotom Q20342G9) | Firewall / Router | 10.1.1.1 |
| UniFi U7 Pro XG AP | WiFi | 10.1.1.19 |
| TrueNAS | Network Storage | 10.1.1.11 |
