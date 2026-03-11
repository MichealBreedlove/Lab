# Network Baseline — iperf3 Matrix

**Date:** 2026-03-10  
**Conditions:** Agent VMs on 1GbE vmbr0; Orin Proxmox on 10GbE eno1→Nexus Eth1/47

## Results

| Source → Dest | Speed | Notes |
|---------------|-------|-------|
| nova → mira | 955 Mbits/sec | 1GbE saturated |
| nova → orin | 2,374 Mbits/sec | Orin 10G NIC inbound |
| mira → nova | 952 Mbits/sec | 1GbE saturated |
| mira → orin | 952 Mbits/sec | 1GbE saturated (nova uplink bottleneck) |
| orin → nova | 2,356 Mbits/sec | Orin 10G NIC outbound |
| orin → mira | 946 Mbits/sec | 1GbE saturated |

## Methodology

```
iperf3 -c <target> -t 5 -P 4 --json
```

Parsed `end.sum_sent.bits_per_second` from JSON output.

## Expected Changes

- **Nova SFP+ cable** (pending): Nova enp6s0 on 10GbE → nova↔TrueNAS jumps to ~10 Gbps
- **Mira BCM57810S** (ordered): Mira gets 10GbE → mira↔* jumps from ~952 to ~9,400+ Mbps
- **Post-VLAN cutover**: All agent VMs move to VLAN 40/50 on dedicated 10G uplinks
