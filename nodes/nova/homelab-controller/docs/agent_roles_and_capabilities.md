# Agent Roles and Capabilities

## Jasper — Coordinator
- **IP**: 10.1.1.150 (GamingPC)
- **Mode**: assisted
- **Capabilities**: task_routing, incident_management, artifact_generation, policy_evaluation, cluster_planning
- **Handles**: investigate_incident, generate_artifact, validate_proposal, document_change
- **Role**: Final decision maker, incident commander, artifact composer

## Nova — Proxmox Optimizer
- **IP**: 10.1.1.21
- **Mode**: autonomous_low_risk
- **Capabilities**: cluster_scan, vm_inventory, storage_analysis, backup_audit, snapshot_cleanup
- **Handles**: audit_proxmox, cluster_scan, optimize_backups, detect_drift
- **Role**: Cluster infrastructure management, backup auditing, drift detection

## Mira — Network Optimizer
- **IP**: 10.1.1.22
- **Mode**: audit
- **Capabilities**: firewall_audit, alias_cleanup, wifi_analysis, network_drift_detection
- **Handles**: audit_firewall, audit_wifi
- **Role**: Firewall rule analysis, WiFi optimization, network hygiene

## Orin — Heavy Analysis
- **IP**: 10.1.1.23
- **Mode**: assisted
- **Capabilities**: log_analysis, incident_investigation, anomaly_detection
- **Handles**: analyze_logs, anomaly_detection, investigate_incident
- **Role**: Large-scale log analysis, anomaly detection, deep investigation

## Execution Modes

| Mode | Allowed Task Types |
|------|-------------------|
| **audit** | Audit tasks only (firewall, wifi, proxmox, cluster scan, drift) |
| **assisted** | Audits + investigations + artifact generation + documentation |
| **autonomous_low_risk** | Audits + documentation + backups (no investigations) |

## Fallback Chains

| Role | Primary → Fallback |
|------|-------------------|
| network_optimizer | Mira → Jasper |
| proxmox_optimizer | Nova → Jasper |
| heavy_analysis | Orin → Jasper |
| investigator | Jasper → Orin |
| documenter | Jasper |
