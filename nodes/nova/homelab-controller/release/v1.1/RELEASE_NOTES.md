# Release v1.1.0 — Platform Operations & Governance

**Date:** 2026-03-05
**Author:** Micheal Breedlove

## Summary

v1.1 adds platform-grade operations, governance, and recruiter-facing portfolio generation on top of the v1.0 autonomous control plane. Six new subsystems bring the total to 16+ integrated modules.

## What's New (P36-P41)

### P36 — Observability + Event Bus
- 7-service Docker Compose stack (Prometheus, Grafana, Loki, Alertmanager, Node Exporter, Promtail, cAdvisor)
- Unified JSONL event bus with rotation
- Alert rules: NodeDown, HighCPU, HighMemory, DiskCritical
- Multi-node scrape configuration

### P37 — Infrastructure Control Plane
- SSH-based node inventory (OS, kernel, CPU, RAM, disks, ZFS, NICs, ports, services)
- Proxmox cluster config export with automatic redaction
- OPNsense manual backup workflow with freshness tracking
- Per-switch backup documentation (Cisco, Brocade, NICGiga)

### P38 — Security Hygiene
- SSH baseline auditing across all nodes
- Automated secret scanning (AWS, GitHub, OpenAI, private keys, passwords)
- Shared redaction library for all emitters
- Pre-commit repo guard (forbidden files + secret scan block)

### P39 — Recruiter Export Pack
- Auto-generated portfolio docs (README, CAPABILITIES, OPERATIONS, SECURITY)
- Status badge generation (shields.io)
- One-command portfolio rendering from live artifacts

### P40 — Continuous Verification
- 6 synthetic endpoint probes (SSH, HTTP, DNS, ping)
- 2 canary function probes (disk write, DNS resolution)
- 4 policy gates (SLO budget, incidents, DR readiness, security audit)
- JSONL history for trend analysis

### P41 — Hardening + Supply Chain
- CycloneDX-lite SBOM with SHA-256 hashes and import analysis
- Build provenance recording (environment, git state)
- Script hardening enforcement (shebangs, bash safety, size limits, banned commands)
- Dependency pinning framework (currently zero third-party deps)

## Architecture

| Layer | Subsystems | Priorities |
|-------|-----------|------------|
| Core | SLO, Snapshots, Planner, Gatekeeper | P1-P10 |
| Reliability | Chaos, Incidents, DR | P21-P30 |
| Operations | Capacity, Bootstrap, Infrastructure | P31-P32, P37 |
| Intelligence | AIOps, Self-Documenting | P33-P34 |
| Observability | Prometheus, Grafana, Loki, Event Bus | P36 |
| Governance | Security, Supply Chain, Verification | P38, P40-P41 |
| Portfolio | Recruiter Export, Badges | P39 |
| Release | Freeze, Audit, Tag | P35, P42 |

## Stats

- **120+ acceptance tests** across 12 test suites
- **12+ dashboard panels** with 5-minute auto-refresh
- **16+ `oc` CLI subcommands** covering all subsystems
- **Zero third-party Python dependencies** (stdlib only)
- **All commits secret-scanned** before push

## Upgrade from v1.0

```bash
cd ~/homelab-controller
git pull origin main
oc test all          # Validate all 120+ tests
oc release tag --apply  # Tag v1.1.0
git push origin v1.1.0
```

## Breaking Changes

None. v1.1 is fully additive over v1.0.
