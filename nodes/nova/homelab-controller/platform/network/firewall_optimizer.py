#!/usr/bin/env python3
"""Firewall/router optimization engine for OPNsense-class systems.

Operational modes:
  audit       — observe and report only (DEFAULT)
  assisted    — generate config changes, wait for approval
  autonomous  — apply only low-risk actions automatically

SAFETY: Never auto-apply WAN rules, default deny, gateway changes,
DHCP subnet changes, DNS resolver changes, VLAN trunk changes,
or management access rules.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
AUDIT_DIR = ROOT / "data" / "network_audit"
CONFIG_FILE = ROOT / "config" / "network_optimizer.json"

NEVER_AUTO_APPLY = [
    "wan_rules", "default_deny_rules", "gateway_changes",
    "dhcp_subnet_changes", "dns_resolver_changes", "vlan_trunk_changes",
    "management_access_rules",
]


def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {"mode": "audit", "enabled": True}


def get_mode():
    return load_config().get("mode", "audit")


def analyze_rules(rules):
    """Analyze firewall rules for issues."""
    findings = []
    seen_sources = {}
    for i, rule in enumerate(rules):
        src = rule.get("source", "")
        dst = rule.get("destination", "")
        action = rule.get("action", "")
        interface = rule.get("interface", "")

        # Shadowed rules: same source+dst+interface but different action
        key = f"{src}:{dst}:{interface}"
        if key in seen_sources:
            findings.append({
                "type": "shadowed_rule",
                "severity": "medium",
                "rule_index": i,
                "detail": f"Rule {i} shadowed by rule {seen_sources[key]}",
                "category": "firewall_rules",
            })
        seen_sources[key] = i

        # Overly broad allow
        if action == "pass" and src == "any" and dst == "any":
            findings.append({
                "type": "overly_broad_allow",
                "severity": "high",
                "rule_index": i,
                "detail": f"Rule {i}: any->any pass on {interface}",
                "category": "firewall_rules",
            })

    return findings


def analyze_aliases(aliases):
    """Detect duplicate or unused aliases."""
    findings = []
    content_map = {}
    for alias in aliases:
        name = alias.get("name", "")
        content = alias.get("content", "")
        if content in content_map:
            findings.append({
                "type": "duplicate_alias",
                "severity": "low",
                "detail": f"Alias '{name}' has same content as '{content_map[content]}'",
                "category": "aliases",
            })
        content_map[content] = name
    return findings


def analyze_dhcp(leases):
    """Check for stale DHCP leases."""
    findings = []
    now = datetime.now(timezone.utc)
    for lease in leases:
        if lease.get("status") == "expired":
            findings.append({
                "type": "stale_dhcp_lease",
                "severity": "low",
                "detail": f"Expired lease for {lease.get('ip', '?')} ({lease.get('hostname', '?')})",
                "category": "dhcp",
            })
    return findings


def generate_report(findings, report_type="firewall_audit"):
    """Generate an audit report from findings."""
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc)
    report = {
        "report_type": report_type,
        "timestamp": ts.isoformat(),
        "mode": get_mode(),
        "finding_count": len(findings),
        "findings": findings,
        "high_severity": len([f for f in findings if f.get("severity") == "high"]),
        "medium_severity": len([f for f in findings if f.get("severity") == "medium"]),
        "low_severity": len([f for f in findings if f.get("severity") == "low"]),
    }
    out_file = AUDIT_DIR / f"{report_type}_{ts.strftime('%Y%m%d_%H%M%S')}.json"
    with open(out_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"[OK] Report: {out_file.name}")
    print(f"     Findings: {len(findings)} (H:{report['high_severity']} M:{report['medium_severity']} L:{report['low_severity']})")
    return report


def _query_memory_for_recommendations(finding_type, tags):
    """P77: Query cluster memory for historical recommendation outcomes."""
    try:
        sys.path.insert(0, str(ROOT / "platform" / "memory"))
        from index import search
        from store import get_memory

        # Find past optimization memories with these tags
        entries = search(category="optimization", tags=tags, status=None, limit=50)
        tag_set = set(tags)
        accepted = 0
        rejected = 0
        rollbacks = 0
        for ie in entries:
            # Require ALL query tags to be present (not just any overlap)
            if not tag_set.issubset(set(ie.get("tags", []))):
                continue
            full = get_memory(ie["memory_id"])
            if not full:
                continue
            outcome = full.get("payload", {}).get("outcome", "")
            if outcome in ("accepted", "applied", "success"):
                accepted += 1
            elif outcome in ("rejected", "declined"):
                rejected += 1
            elif outcome in ("rollback", "reverted"):
                rollbacks += 1
        return {"accepted": accepted, "rejected": rejected, "rollbacks": rollbacks,
                "total": accepted + rejected + rollbacks}
    except Exception:
        return None


def generate_recommendations(findings):
    """Generate safe recommendations based on findings, informed by cluster memory."""
    recs = []
    for f in findings:
        cat = f.get("category", "")
        rec = None
        if cat in NEVER_AUTO_APPLY or f.get("severity") == "high":
            rec = {
                "finding": f["type"],
                "action": "manual_review_required",
                "auto_applicable": False,
                "detail": f["detail"],
            }
        elif f.get("severity") == "low":
            rec = {
                "finding": f["type"],
                "action": "assisted_cleanup",
                "auto_applicable": get_mode() == "autonomous",
                "detail": f["detail"],
            }
        else:
            rec = {
                "finding": f["type"],
                "action": "review_and_fix",
                "auto_applicable": False,
                "detail": f["detail"],
            }

        # P77: Enrich with memory history
        mem = _query_memory_for_recommendations(f["type"], ["firewall", f["type"]])
        if mem and mem["total"] > 0:
            rec["memory_history"] = mem
            # Suppress recommendations that were repeatedly rejected
            if mem["rejected"] >= 3 and mem["accepted"] == 0:
                rec["action"] = "suppressed_by_memory"
                rec["auto_applicable"] = False
                rec["suppression_reason"] = f"Rejected {mem['rejected']} times previously"
            # Boost if historically accepted
            elif mem["accepted"] >= 2 and mem["rollbacks"] == 0:
                rec["memory_boost"] = True

        recs.append(rec)
    return recs


def run_audit(sample_data=None):
    """Run a full firewall audit."""
    if sample_data is None:
        sample_data = {
            "rules": [
                {"source": "10.1.1.0/24", "destination": "any", "action": "pass", "interface": "LAN"},
                {"source": "any", "destination": "any", "action": "pass", "interface": "LAN"},
            ],
            "aliases": [
                {"name": "HomeNet", "content": "10.1.1.0/24"},
                {"name": "LAN_Net", "content": "10.1.1.0/24"},
            ],
            "dhcp_leases": [
                {"ip": "10.1.1.200", "hostname": "old-device", "status": "expired"},
            ],
        }

    findings = []
    findings.extend(analyze_rules(sample_data.get("rules", [])))
    findings.extend(analyze_aliases(sample_data.get("aliases", [])))
    findings.extend(analyze_dhcp(sample_data.get("dhcp_leases", [])))

    report = generate_report(findings, "firewall_audit")
    recs = generate_recommendations(findings)
    report["recommendations"] = recs
    return report


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "audit"
    if cmd == "audit":
        run_audit()
    elif cmd == "mode":
        print(f"  Mode: {get_mode()}")
    else:
        print("Usage: firewall_optimizer.py [audit|mode]")


if __name__ == "__main__":
    main()
