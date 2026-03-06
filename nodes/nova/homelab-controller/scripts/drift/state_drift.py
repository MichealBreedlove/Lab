#!/usr/bin/env python3
"""Compare desired vs observed state and produce drift reports."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DESIRED_DIR = ROOT / "state" / "desired"
OBSERVED_DIR = ROOT / "state" / "observed"
DRIFT_DIR = ROOT / "state" / "drift"
DASHBOARD_DATA = ROOT / "dashboard" / "static" / "data"


def diff_node(name):
    """Compare desired vs observed for a node. Return list of drifts."""
    desired_f = DESIRED_DIR / name / "desired.json"
    observed_f = OBSERVED_DIR / name / "observed.json"
    drifts = []

    if not desired_f.exists():
        return [{"field": "desired_state", "severity": "error", "msg": "No desired state defined"}]
    if not observed_f.exists():
        return [{"field": "observed_state", "severity": "error", "msg": "No observed state collected"}]

    with open(desired_f) as f:
        desired = json.load(f)
    with open(observed_f) as f:
        observed = json.load(f)

    if not observed.get("reachable"):
        return [{"field": "connectivity", "severity": "critical", "msg": f"{name} is unreachable"}]

    # Check services
    for svc in desired.get("services", []):
        actual = observed.get("services", {}).get(svc, "unknown")
        if actual != "active":
            drifts.append({
                "field": f"service.{svc}",
                "severity": "warning",
                "expected": "active",
                "actual": actual,
                "msg": f"Service {svc} is {actual} (expected active)"
            })

    # Check ports
    for port in desired.get("ports", []):
        actual = observed.get("ports", {}).get(str(port), "unknown")
        if actual != "open":
            drifts.append({
                "field": f"port.{port}",
                "severity": "warning",
                "expected": "open",
                "actual": actual,
                "msg": f"Port {port} is {actual} (expected open)"
            })

    # Check packages
    for pkg in desired.get("packages", []):
        actual = observed.get("packages", {}).get(pkg, "unknown")
        if actual != "installed":
            drifts.append({
                "field": f"package.{pkg}",
                "severity": "warning",
                "expected": "installed",
                "actual": actual,
                "msg": f"Package {pkg} is {actual} (expected installed)"
            })

    # Check SSH config
    for key, expected_val in desired.get("ssh_config", {}).items():
        actual = observed.get("ssh_config", {}).get(key, "unknown")
        if actual.lower() != expected_val.lower():
            drifts.append({
                "field": f"ssh.{key}",
                "severity": "warning",
                "expected": expected_val,
                "actual": actual,
                "msg": f"SSH {key} = {actual} (expected {expected_val})"
            })

    # Check firewall
    fw_desired = desired.get("firewall", {})
    fw_observed = observed.get("firewall", {})
    if fw_desired.get("ufw_enabled") and not fw_observed.get("ufw_active"):
        drifts.append({
            "field": "firewall.ufw",
            "severity": "critical",
            "expected": "active",
            "actual": "inactive",
            "msg": "UFW firewall is not active"
        })

    return drifts


def compute_status(all_drifts):
    """Compute overall status from drift results."""
    has_critical = any(
        d["severity"] == "critical"
        for drifts in all_drifts.values()
        for d in drifts
    )
    has_warning = any(
        d["severity"] in ("warning", "error")
        for drifts in all_drifts.values()
        for d in drifts
    )
    if has_critical:
        return "RED"
    if has_warning:
        return "YELLOW"
    return "GREEN"


def generate_report(all_drifts, status):
    """Generate drift_report.json and drift_report.md."""
    DRIFT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    total_drifts = sum(len(d) for d in all_drifts.values())

    # JSON report
    report = {
        "timestamp": timestamp,
        "status": status,
        "total_drifts": total_drifts,
        "nodes": {}
    }
    for name, drifts in all_drifts.items():
        report["nodes"][name] = {
            "drift_count": len(drifts),
            "drifts": drifts
        }

    with open(DRIFT_DIR / "drift_report.json", "w") as f:
        json.dump(report, f, indent=2)

    # Markdown report
    lines = [
        f"# Drift Report -- {timestamp}",
        f"",
        f"Status: **{status}** | Total drifts: **{total_drifts}**",
        f"",
    ]

    for name, drifts in all_drifts.items():
        icon = "[OK]" if not drifts else "[DRIFT]"
        lines.append(f"## {name} {icon}")
        if not drifts:
            lines.append("No drift detected.\n")
        else:
            for d in drifts:
                sev = d["severity"].upper()
                lines.append(f"- **{sev}** `{d['field']}`: {d['msg']}")
            lines.append("")

    with open(DRIFT_DIR / "drift_report.md", "w") as f:
        f.write("\n".join(lines))

    # Dashboard data
    DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)
    with open(DASHBOARD_DATA / "drift_status.json", "w") as f:
        json.dump({
            "timestamp": timestamp,
            "status": status,
            "total_drifts": total_drifts,
            "pass": total_drifts == 0,
        }, f, indent=2)

    return report


def main():
    with open(ROOT / "config" / "desired_state.json") as f:
        config = json.load(f)

    print("Computing drift...")
    all_drifts = {}

    for name in config.get("nodes", {}):
        drifts = diff_node(name)
        all_drifts[name] = drifts
        icon = "[OK]" if not drifts else f"[{len(drifts)} drifts]"
        print(f"  {name}: {icon}")

    # Infrastructure drift
    infra_drifts = []
    infra_observed_f = OBSERVED_DIR / "infrastructure" / "observed.json"
    if infra_observed_f.exists():
        with open(infra_observed_f) as f:
            infra = json.load(f)
        if not infra.get("opnsense", {}).get("reachable"):
            infra_drifts.append({"field": "opnsense", "severity": "critical", "msg": "OPNsense unreachable"})
        for pve_name, pve in infra.get("proxmox", {}).get("nodes", {}).items():
            if not pve.get("reachable"):
                infra_drifts.append({"field": f"proxmox.{pve_name}", "severity": "critical", "msg": f"{pve_name} unreachable"})
    all_drifts["infrastructure"] = infra_drifts

    status = compute_status(all_drifts)
    report = generate_report(all_drifts, status)

    print(f"\nDrift status: {status} ({report['total_drifts']} drift(s))")
    print(f"Reports: {DRIFT_DIR}/drift_report.{{json,md}}")

    return 0 if status == "GREEN" else 1


if __name__ == "__main__":
    sys.exit(main())
