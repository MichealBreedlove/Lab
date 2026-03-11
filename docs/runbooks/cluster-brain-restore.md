# Runbook: Cluster Brain Restore

**Date:** 2026-03-10  
**Status:** Resolved  
**Author:** Jasper (AI orchestrator)

## Summary

The homelab cluster brain (custom Python agent system on nova) was orphaned after the gateway host (10.1.1.20) went offline. All 4 agents were failing heartbeats with "unauthorized". Restored full cluster operation.

## Symptoms

- Agent VMs (nova/mira/orin) showing `Heartbeat failed: unauthorized` in `openclaw-agent.service` logs
- API at `http://10.1.1.21:8081` returning `Token validation failed`
- `active_tokens.json` in wrong format (dict instead of list)

## Root Cause

The `active_tokens.json` file was hand-crafted in an incorrect schema. The `token_issuer.py` `validate_token()` function expects:
- `tokens` as a **list** of records (not a dict)
- Each record must have `token_id`, `token_hash` (SHA-256 of raw secret), `role`, `principal_type`, `expires_at`, `revoked`

## Resolution

1. Identified correct token format by reading `token_issuer.py`
2. Generated correct token record:
   ```python
   import hashlib
   RAW = "94265cc3491a9340853793f8d8e3a0611f76946f0756d350"
   token_hash = hashlib.sha256(RAW.encode()).hexdigest()
   token_id = f"hlab_{RAW[:8]}"
   ```
3. Wrote correct `active_tokens.json` to `/home/nova/Lab/nodes/nova/homelab-controller/artifacts/identity/`
4. Restarted API server: `pkill -f api/server.py && cd ~/Lab/nodes/nova/homelab-controller && nohup python3 platform/api/server.py &`
5. All 4 agents came online immediately

## Agent Roles

| Agent | Role | Capabilities |
|-------|------|-------------|
| jasper | coordinator | task_routing, incident_management |
| nova | proxmox_optimizer | cluster_scan, vm_inventory, storage_analysis |
| mira | network_optimizer | firewall_audit, network_drift_detection |
| orin | heavy_analysis | log_analysis, incident_investigation, anomaly_detection |

## API Access

```bash
TOKEN="hlab_94265cc3491a9340853793f8d8e3a0611f76946f0756d350"
curl -H "Authorization: Bearer $TOKEN" http://10.1.1.21:8081/cluster/agents
```

## Prevention

- Add systemd watchdog to auto-restart the API server on crash
- Consider persisting a valid token file to NAS so it survives reimaging
