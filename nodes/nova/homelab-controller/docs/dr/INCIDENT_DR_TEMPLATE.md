# DR Incident: [NODE] — [DATE]

**Type:** Disaster Recovery
**Node:** [jasper/nova/mira/orin]
**Severity:** SEV[1/2/3]
**Started:** YYYY-MM-DD HH:MM UTC
**Restored:** YYYY-MM-DD HH:MM UTC
**MTTR:** X minutes

## Trigger

[What caused the need for DR? Hardware failure, config corruption, OS reinstall, etc.]

## Restore Method

- [ ] Automated (`oc dr restore --apply`)
- [ ] Semi-automated (dry-run + manual steps)
- [ ] Manual (checklist-based)

## Timeline

| Time | Event |
|---|---|
| HH:MM | [Failure detected] |
| HH:MM | [DR initiated] |
| HH:MM | [Preflight passed/failed] |
| HH:MM | [Restore started] |
| HH:MM | [Restore completed] |
| HH:MM | [Validation passed] |

## Validation Results

- Services: [X/Y passing]
- Ports: [X/Y open]
- Connectivity: [X/Y reachable]

## Issues Encountered

[Any problems during restore]

## Action Items

- [ ] [Preventive action]
- [ ] [Documentation update]
- [ ] [Automation improvement]

## Notes

[Additional context]
