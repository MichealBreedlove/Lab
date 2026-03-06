# Platform API

## Overview

The Platform API is an internal HTTP control interface running on Nova (port 8081). It provides programmatic access to the homelab control plane for triggering changes, chaos experiments, snapshots, and incident logging.

## Security

- **Network restriction:** Only accessible from 10.1.1.0/24 (LAN) and localhost
- **No authentication tokens stored in repo**
- Runs as a systemd user service (`homelab-platform-api.service`)

## Endpoints

### `GET /`
Returns API status, version, and available endpoints.

### `GET /topology`
Runs a device connectivity scan and returns current network topology with reachability status for all managed nodes.

### `POST /change`
Creates a full change log entry with diff, validation, and rendered report.

```json
{
  "trigger": "manual|proxmox_config|opnsense_backup|remediation|chaos_experiment|dr_drill|drift_detection",
  "summary": "Description of the change"
}
```

Returns: `{ "change_id": "CHG-...", "status": "completed" }`

### `POST /chaos`
Triggers a reliability demo scenario with change logging.

```json
{
  "scenario": "gateway_restart_outage"
}
```

Returns: `{ "change_id": "CHG-...", "scenario": "...", "exit_code": 0 }`

### `POST /incident`
Logs an incident with associated change entry.

```json
{
  "title": "Incident description",
  "severity": "warning|critical|info"
}
```

### `POST /snapshot`
Runs the full drift detection pipeline and generates a change log entry.

Returns: `{ "change_id": "CHG-...", "drift_status": "GREEN|YELLOW|RED", "status": "completed" }`

## Evidence Generation

Every API call that modifies state produces:
1. A unique `CHG-*` change log entry
2. A configuration diff (`diff.md`)
3. An 8-point connectivity validation (`validation.md`)
4. A rendered change report (`change.md`)
5. An evidence folder for artifacts

## CLI Wrapper

```bash
oc platform status     # Check API health
oc platform start      # Install + start service
oc platform stop       # Stop service
oc platform chaos      # Trigger chaos via API
oc platform change     # Trigger change pipeline
oc platform snapshot   # Trigger snapshot pipeline
```

## Dashboard Integration

The API writes `platform_status.json` to `dashboard/static/data/` with:
- API running status
- Last request details (endpoint, timestamp, IP)
- Last change ID
- Total request count

## Service Management

```bash
# Start/stop
systemctl --user start homelab-platform-api
systemctl --user stop homelab-platform-api
systemctl --user status homelab-platform-api

# Logs
journalctl --user -u homelab-platform-api -f
```
