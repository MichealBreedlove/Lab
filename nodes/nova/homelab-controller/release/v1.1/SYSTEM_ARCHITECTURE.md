# System Architecture — v1.1

## Cluster Topology

```
┌──────────────────────────────────────────────────┐
│                  OPNsense Gateway                │
│                   10.1.1.1                       │
└──────────┬──────────┬──────────┬─────────────────┘
           │          │          │
    ┌──────┴──┐ ┌─────┴───┐ ┌───┴─────┐ ┌─────────┐
    │  Nova   │ │  Mira   │ │  Orin   │ │ Jasper  │
    │ .21     │ │ .22     │ │ .23     │ │ .150    │
    │Controller│ │ Worker  │ │ Worker  │ │GPU+Gate │
    │ N305    │ │i7-2600K │ │R630 2xE5│ │i9-13900K│
    │ 32GB    │ │ 16GB    │ │ 16GB ECC│ │64GB+4090│
    └─────────┘ └─────────┘ └─────────┘ └─────────┘
```

## Subsystem Map (v1.1)

### Core Control Plane (P1-P10)
- **Snapshot Pipeline**: Periodic system state collection
- **SLO Monitor**: Error budget tracking with burn-rate alerts
- **Planner**: Action proposal and scheduling
- **Gatekeeper**: Policy enforcement before execution

### Reliability (P21-P30)
- **Chaos Engine**: Fault injection with automated recovery
- **Incident Manager**: Detection, correlation, timeline, postmortem
- **Disaster Recovery**: One-command restore, drill validation, MTTR tracking

### Operations (P31-P32, P37)
- **Node Bootstrap**: Zero-touch provisioning with profiles
- **Capacity Manager**: Forecasting, recommendations, rebalancing
- **Infrastructure Backup**: Proxmox/OPNsense/switch config management

### Intelligence (P33-P34)
- **Self-Documenting**: Auto-generated topology, services, deps, diagrams
- **AIOps**: Anomaly detection, incident correlation, LLM analysis

### Observability (P36)
- **Metrics**: Prometheus + Node Exporter + cAdvisor
- **Visualization**: Grafana dashboards
- **Logs**: Loki + Promtail
- **Alerts**: Alertmanager with rules
- **Event Bus**: JSONL unified event stream

### Governance (P38, P40-P41)
- **Security**: Baseline auditing, secret scanning, redaction, repo guard
- **Verification**: Synthetic probes, canaries, policy gates
- **Supply Chain**: SBOM, provenance, hardening, dependency pinning

### Portfolio (P39)
- **Recruiter Export**: Auto-generated docs, badges, capability maps

## Data Flow

```
Nodes → SSH → Snapshot/Inventory → Artifacts → Dashboard
                    ↓
              SLO/Capacity/AIOps → Recommendations
                    ↓
              Gatekeeper → Approved Actions → Nodes
                    ↓
              Event Bus → History/Correlation
```

## CLI Summary

| Command | Purpose |
|---------|---------|
| `oc health` | Node health collection |
| `oc slo` | SLO status and evaluation |
| `oc chaos` | Chaos experiment management |
| `oc incident` | Incident lifecycle |
| `oc dr` | Disaster recovery |
| `oc bootstrap` | Node provisioning |
| `oc capacity` | Capacity planning |
| `oc docs` | Documentation generation |
| `oc aiops` | AI operations analysis |
| `oc obs` | Observability stack |
| `oc infra` | Infrastructure backup |
| `oc sec` | Security auditing |
| `oc portfolio` | Portfolio export |
| `oc verify` | Continuous verification |
| `oc supply` | Supply chain management |
| `oc release` | Release management |
| `oc test` | Acceptance testing |
```
