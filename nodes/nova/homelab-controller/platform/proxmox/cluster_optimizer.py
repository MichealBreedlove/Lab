#!/usr/bin/env python3
"""Proxmox cluster optimization engine.

Operational modes:
  audit              — observe and report only (DEFAULT)
  assisted           — generate changes, wait for approval
  autonomous_low_risk — apply only low-risk actions automatically

LOW RISK AUTONOMOUS ACTIONS:
  - Add standardized tags
  - Generate documentation notes
  - Normalize backup schedule metadata
  - Flag outdated templates
  - Create config snapshots

NEVER AUTO-APPLY:
  - Bridge changes
  - Bond changes
  - VLAN trunk changes
  - Storage migration
  - HA policy changes
  - Cluster quorum changes
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
AUDIT_DIR = ROOT / "data" / "proxmox_audit"
CONFIG_FILE = ROOT / "config" / "proxmox_optimizer.json"

NEVER_AUTO_APPLY = [
    "bridge_changes", "bond_changes", "vlan_trunk_changes",
    "storage_migration", "ha_policy_changes", "cluster_quorum_changes",
]

LOW_RISK_ACTIONS = [
    "add_tags", "generate_notes", "normalize_backup_metadata",
    "flag_outdated_templates", "create_config_snapshot",
]


def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {"mode": "audit", "enabled": True}


def get_mode():
    return load_config().get("mode", "audit")


def analyze_vms(vms):
    """Analyze VM inventory for optimization opportunities."""
    findings = []
    for vm in vms:
        vmid = vm.get("vmid", "?")
        name = vm.get("name", "?")
        tags = vm.get("tags", "")
        notes = vm.get("notes", "")
        snapshots = vm.get("snapshots", [])
        memory = vm.get("maxmem", 0)
        cpu = vm.get("cpus", 0)
        status = vm.get("status", "unknown")

        # Missing tags
        if not tags:
            findings.append({
                "type": "missing_tags",
                "severity": "low",
                "vmid": vmid,
                "detail": f"VM {vmid} ({name}) has no tags",
                "action": "add_tags",
            })

        # Missing notes
        if not notes:
            findings.append({
                "type": "missing_notes",
                "severity": "low",
                "vmid": vmid,
                "detail": f"VM {vmid} ({name}) has no description/notes",
                "action": "generate_notes",
            })

        # Orphaned snapshots (>30 days old)
        for snap in snapshots:
            age_days = snap.get("age_days", 0)
            if age_days > 30:
                findings.append({
                    "type": "orphaned_snapshot",
                    "severity": "medium",
                    "vmid": vmid,
                    "detail": f"VM {vmid} snapshot '{snap.get('name', '?')}' is {age_days} days old",
                    "action": "review_snapshot",
                })

        # Oversized allocation (stopped VM with >8GB RAM)
        if status == "stopped" and memory > 8 * 1024 * 1024 * 1024:
            findings.append({
                "type": "oversized_stopped_vm",
                "severity": "low",
                "vmid": vmid,
                "detail": f"VM {vmid} ({name}) stopped with {memory // (1024**3)}GB RAM allocated",
                "action": "review_allocation",
            })

    return findings


def analyze_storage(storage_pools):
    """Analyze storage pool balance."""
    findings = []
    usages = []
    for pool in storage_pools:
        name = pool.get("storage", "?")
        used_pct = pool.get("used_fraction", 0) * 100
        usages.append(used_pct)

        if used_pct > 85:
            findings.append({
                "type": "storage_high_usage",
                "severity": "high" if used_pct > 95 else "medium",
                "detail": f"Storage '{name}' at {used_pct:.1f}% capacity",
                "action": "review_storage",
            })

    # Check imbalance
    if len(usages) > 1:
        spread = max(usages) - min(usages)
        if spread > 40:
            findings.append({
                "type": "storage_imbalance",
                "severity": "medium",
                "detail": f"Storage usage spread: {spread:.1f}% between pools",
                "action": "review_storage_balance",
            })

    return findings


def analyze_backups(backup_jobs):
    """Check backup schedule consistency."""
    findings = []
    for job in backup_jobs:
        if not job.get("enabled", True):
            findings.append({
                "type": "disabled_backup_job",
                "severity": "medium",
                "detail": f"Backup job '{job.get('id', '?')}' is disabled",
                "action": "review_backup",
            })
    return findings


def _query_proxmox_memory(finding_type):
    """P77: Check cluster memory for historical Proxmox optimization outcomes."""
    try:
        sys.path.insert(0, str(ROOT / "platform" / "memory"))
        from index import search
        from store import get_memory
        required_tags = {"proxmox", finding_type}
        entries = search(category="optimization", tags=["proxmox", finding_type], status=None, limit=50)
        accepted = sum(1 for ie in entries
                       if required_tags.issubset(set(ie.get("tags", [])))
                       and (get_memory(ie["memory_id"]) or {}).get("payload", {}).get("outcome") in ("accepted", "applied"))
        rejected = sum(1 for ie in entries
                       if required_tags.issubset(set(ie.get("tags", [])))
                       and (get_memory(ie["memory_id"]) or {}).get("payload", {}).get("outcome") in ("rejected", "declined"))
        rollbacks = sum(1 for ie in entries
                        if required_tags.issubset(set(ie.get("tags", [])))
                        and (get_memory(ie["memory_id"]) or {}).get("payload", {}).get("outcome") in ("rollback", "reverted"))
        return {"accepted": accepted, "rejected": rejected, "rollbacks": rollbacks,
                "total": accepted + rejected + rollbacks}
    except Exception:
        return None


def generate_recommendations(findings):
    """Generate recommendations with safety classification, informed by cluster memory."""
    recs = []
    mode = get_mode()
    for f in findings:
        action = f.get("action", "manual_review")
        auto_applicable = (
            mode in ("autonomous_low_risk", "autonomous") and
            action in LOW_RISK_ACTIONS and
            action not in NEVER_AUTO_APPLY
        )
        rec = {
            "finding": f["type"],
            "action": action,
            "auto_applicable": auto_applicable,
            "severity": f.get("severity", "medium"),
            "detail": f["detail"],
        }
        # P77: Enrich with memory history
        mem = _query_proxmox_memory(f["type"])
        if mem and mem["total"] > 0:
            rec["memory_history"] = mem
            if mem["rejected"] >= 3 and mem["accepted"] == 0:
                rec["action"] = "suppressed_by_memory"
                rec["auto_applicable"] = False
                rec["suppression_reason"] = f"Rejected {mem['rejected']} times previously"
            elif mem["accepted"] >= 2 and mem["rollbacks"] == 0:
                rec["memory_boost"] = True
        recs.append(rec)
    return recs


def run_audit(cluster_data=None):
    """Run full cluster audit."""
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    if cluster_data is None:
        cluster_data = {
            "nodes": [
                {"node": "PROXMOX", "ip": "10.1.1.2", "status": "online"},
                {"node": "PROXMOX-2", "ip": "10.1.1.4", "status": "online"},
                {"node": "PROXMOX-3", "ip": "10.1.1.5", "status": "online"},
            ],
            "vms": [
                {"vmid": 100, "name": "nova", "tags": "openclaw,controller", "notes": "Control plane", "status": "running", "maxmem": 34359738368, "cpus": 8, "snapshots": []},
                {"vmid": 101, "name": "mira", "tags": "", "notes": "", "status": "running", "maxmem": 17179869184, "cpus": 8, "snapshots": [{"name": "pre-upgrade", "age_days": 45}]},
                {"vmid": 102, "name": "orin", "tags": "compute", "notes": "", "status": "running", "maxmem": 17179869184, "cpus": 32, "snapshots": []},
            ],
            "storage": [
                {"storage": "local", "used_fraction": 0.45},
                {"storage": "local-lvm", "used_fraction": 0.62},
            ],
            "backup_jobs": [
                {"id": "backup-1", "enabled": True},
            ],
        }

    findings = []
    findings.extend(analyze_vms(cluster_data.get("vms", [])))
    findings.extend(analyze_storage(cluster_data.get("storage", [])))
    findings.extend(analyze_backups(cluster_data.get("backup_jobs", [])))
    recs = generate_recommendations(findings)

    ts = datetime.now(timezone.utc)
    report = {
        "report_type": "proxmox_cluster_audit",
        "timestamp": ts.isoformat(),
        "mode": get_mode(),
        "node_count": len(cluster_data.get("nodes", [])),
        "vm_count": len(cluster_data.get("vms", [])),
        "finding_count": len(findings),
        "findings": findings,
        "recommendations": recs,
        "high_severity": len([f for f in findings if f.get("severity") == "high"]),
        "medium_severity": len([f for f in findings if f.get("severity") == "medium"]),
        "low_severity": len([f for f in findings if f.get("severity") == "low"]),
    }

    out_file = AUDIT_DIR / f"proxmox_audit_{ts.strftime('%Y%m%d_%H%M%S')}.json"
    with open(out_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"[OK] Proxmox audit: {out_file.name}")
    print(f"     Nodes: {report['node_count']}, VMs: {report['vm_count']}, Findings: {len(findings)}")
    print(f"     Severity: H:{report['high_severity']} M:{report['medium_severity']} L:{report['low_severity']}")
    return report


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "audit"
    if cmd == "audit":
        run_audit()
    elif cmd == "mode":
        print(f"  Mode: {get_mode()}")
    else:
        print("Usage: cluster_optimizer.py [audit|mode]")


if __name__ == "__main__":
    main()
