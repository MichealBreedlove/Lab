# Infrastructure Optimization

## Overview

Domain-specific optimization engines for firewall/router, WiFi, and Proxmox cluster infrastructure. Each engine follows the observe → analyze → propose → validate → apply pattern with strict safety controls.

## Operational Modes

| Mode | Description | Auto-Apply |
|------|-------------|------------|
| **audit** | Observe and report only (DEFAULT) | No |
| **assisted** | Generate config changes, wait for approval | No |
| **autonomous_low_risk** | Apply only low-risk actions automatically | Low-risk only |

## Firewall / Router Engine

**Target**: OPNsense (10.1.1.1)

### Capabilities
- Analyze firewall rules for shadowed/duplicate/overly-broad entries
- Detect duplicate aliases and unused objects
- Check for stale DHCP leases
- Generate cleanup and normalization reports

### Safety: NEVER Auto-Apply
- WAN rules
- Default deny rules
- Gateway changes
- DHCP subnet changes
- DNS resolver changes
- VLAN trunk changes
- Management access rules

### Assisted Actions
- Rule reordering suggestions
- Alias normalization
- Comment and documentation improvements

## WiFi / Access Point Engine

**Target**: UniFi U7 Pro XG (10.1.1.19)

### Capabilities
- Analyze channel assignments for interference
- Detect excessive transmit power (sticky client risk)
- Generate channel reassignment suggestions
- Power adjustment recommendations

### Mode: ASSISTED ONLY
WiFi changes are never auto-applied. All suggestions require human review.

### Safety: NEVER Auto-Apply
- SSID changes
- Security mode changes
- Controller migrations
- Site configuration changes

## Proxmox Cluster Engine

**Target**: CL-1 cluster (10.1.1.2, 10.1.1.4, 10.1.1.5)

### Capabilities
- Detect missing tags and documentation
- Find orphaned snapshots (>30 days)
- Check storage pool balance
- Audit backup schedule consistency
- Flag oversized stopped VMs

### Low-Risk Autonomous Actions
- Add standardized tags
- Generate documentation notes
- Normalize backup schedule metadata
- Flag outdated templates
- Create config snapshots

### Safety: NEVER Auto-Apply
- Bridge changes
- Bond changes
- VLAN trunk changes
- Storage migration
- HA policy changes
- Cluster quorum changes

## Pre-Change Safety Sequence

Every infrastructure change follows:

1. **Backup** configuration
2. **Record** baseline state
3. **Test** connectivity
4. **Apply** change (if policy allows)
5. **Validate** network access
6. **Rollback** if validation fails

Rollback artifacts are generated for every proposed change.
