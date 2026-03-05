# Restore Checklist

Use this checklist for manual or semi-automated node restoration.

## Pre-Restore

- [ ] Identify which node needs restoration
- [ ] Confirm Lab repo is accessible (clone/pull)
- [ ] Verify network connectivity to cluster
- [ ] Check current node state (is it partially working or fresh install?)

## Per-Node Restore

### Nova (Controller)

- [ ] Install packages: `apt install python3 python3-pip python3-yaml git ansible jq`
- [ ] Clone/pull Lab repo
- [ ] Copy `nodes/nova/openclaw/` → `~/.openclaw/`
- [ ] Copy `nodes/nova/homelab-controller/` → `~/homelab-controller/`
- [ ] Enable systemd user services: `systemctl --user enable --now openclaw-node`
- [ ] Enable backup timer: `systemctl --user enable --now lab-backup.timer`
- [ ] Run `oc dr validate --node nova`

### Mira / Orin (Compute)

- [ ] Install packages: `apt install python3 git`
- [ ] Clone/pull Lab repo
- [ ] Copy `nodes/<name>/openclaw/` → `~/.openclaw/`
- [ ] Enable systemd user services: `systemctl --user enable --now openclaw-node`
- [ ] Run `oc dr validate --node <name>`

### Jasper (Windows Gateway)

- [ ] Install: git, PowerShell 7
- [ ] Clone/pull Lab repo
- [ ] Copy `nodes/jasper/openclaw/config/` → `~/.openclaw/`
- [ ] Run `openclaw gateway start`
- [ ] Verify scheduled tasks (OpenClawGateway, LabBackup)
- [ ] Run `oc dr validate --node jasper` (from Nova)

## Post-Restore

- [ ] Verify all SLOs are reporting (`oc slo status`)
- [ ] Confirm backup pipeline runs (`oc backup`)
- [ ] Check node connectivity (`oc ping`)
- [ ] Run full test suite (`oc test all`)
- [ ] Document the restore in an incident file if applicable
