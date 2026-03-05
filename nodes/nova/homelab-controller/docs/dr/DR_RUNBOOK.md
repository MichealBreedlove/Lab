# DR Runbook — Disaster Recovery

## Overview

This runbook covers restoring any node in the homelab cluster from the Lab repository backup.

## Prerequisites

- Access to `github.com/MichealBreedlove/Lab` (clone or pull)
- Python 3 + git installed on the target node
- Network connectivity to other cluster nodes
- For destructive restores: break-glass token (see below)

## Quick Restore (Dry Run)

```bash
cd ~/homelab-controller
oc dr preflight --node nova
oc dr restore --node nova --dry-run
```

Review the plan in `artifacts/dr/restore_plan.json`, then apply:

```bash
oc dr restore --node nova --apply
oc dr validate --node nova
```

## Full Restore Procedure

1. **Clone the Lab repo** on the target machine:
   ```bash
   git clone https://github.com/MichealBreedlove/Lab.git
   cd Lab/nodes/nova/homelab-controller
   ```

2. **Run preflight**:
   ```bash
   python3 scripts/dr/dr_preflight.py --node nova
   ```

3. **Review and execute restore**:
   ```bash
   python3 scripts/dr/dr_restore.py --node nova --dry-run
   # Review artifacts/dr/restore_plan.json
   python3 scripts/dr/dr_restore.py --node nova --apply
   ```

4. **Validate**:
   ```bash
   python3 scripts/dr/dr_validate.py --node nova
   ```

5. **Run acceptance tests**:
   ```bash
   bash scripts/dr/test_priority30_dr.sh
   ```

## Break-Glass Token

Destructive restore actions (overwriting configs, restarting services) require a break-glass token:

```bash
# Generate a break-glass token (valid for 30 minutes)
date +%s | sha256sum | head -c 64 > config/break_glass.token
```

The token must be:
- Present at `config/break_glass.token`
- Less than 30 minutes old (configurable in `dr_policy.json`)
- Never committed to git (listed in `.gitignore`)

## DR Drill

Run a safe, non-destructive drill to test restore readiness:

```bash
oc dr drill --node nova
```

This will:
1. Run preflight checks
2. Capture baseline inventory
3. Simulate safe failures (stop services, rename configs)
4. Validate (expecting failures)
5. Undo simulations
6. Run restore dry-run
7. Re-validate
8. Generate report with MTTR

## Escalation

If automated restore fails:
1. Check `artifacts/dr/restore_plan.json` for specific failures
2. Manually apply steps from `RESTORE_CHECKLIST.md`
3. If node is unrecoverable, follow the rebuild procedure in `docs/runbooks/restore.md`
