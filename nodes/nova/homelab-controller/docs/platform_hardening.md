# Platform Hardening Checklist (Phase 7)

## Reliability

- [ ] Event bus log rotation (cap at 10K events, archive older)
- [ ] Task bus cleanup (archive completed tasks older than 7 days)
- [ ] Memory store data directory size monitoring
- [ ] Agent heartbeat stress test (simulate rapid degraded→offline transitions)
- [ ] Task routing failover test (kill agent mid-task, verify reassignment)
- [ ] Recovery engine stress test (multiple simultaneous service failures)
- [ ] Platform API restart recovery (verify state survives restart)

## Safety Validation

- [ ] Verify all NEVER_AUTO_APPLY categories are enforced in:
  - Firewall optimizer
  - WiFi optimizer
  - Proxmox optimizer
  - Distributed execution policy
- [ ] Verify high-risk tasks never auto-reassigned on failover
- [ ] Verify memory cannot override approval requirements
- [ ] Verify self-improvement cannot auto-promote policy changes
- [ ] Test viewer role cannot access write endpoints
- [ ] Test rate limiting under sustained load

## Data Integrity

- [ ] Memory lifecycle tick runs without errors
- [ ] Memory rollup summaries are coherent
- [ ] Knowledge graph traversal handles cycles
- [ ] Investigation context handles empty/corrupt memory gracefully
- [ ] Remediation artifacts are well-formed after memory enrichment

## Backup / Restore

- [ ] Platform state backup script (config/ + data/ snapshot)
- [ ] Restore from backup test
- [ ] Git push all state changes
- [ ] Verify .gitignore excludes runtime data correctly

## Network Safety

- [ ] Agent runtime handles API unreachable gracefully
- [ ] Agent re-registers after API restart
- [ ] No credentials in logs or event bus
- [ ] Token in agent config is not committed to git

## Monitoring

- [ ] Agent health visible in dashboard
- [ ] Memory stats visible in dashboard
- [ ] Task queue visible in dashboard
- [ ] Daily scorecard generation works end-to-end

## Documentation Gaps

- [ ] README.md reflects final architecture
- [ ] All API endpoints documented
- [ ] CLI `oc` subcommands documented
- [ ] Agent deployment documented
