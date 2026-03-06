#!/usr/bin/env python3
"""WiFi / Access Point optimization engine.

Operational mode: ASSISTED ONLY (never autonomous for WiFi).

SAFETY: Never auto-apply SSID changes, security mode changes,
controller migrations, or site configuration changes.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
AUDIT_DIR = ROOT / "data" / "network_audit"

NEVER_AUTO_APPLY = [
    "ssid_changes", "security_mode_changes", "controller_migrations",
    "site_configuration_changes",
]


def analyze_channels(ap_data):
    """Analyze AP channel assignments for interference and overlap."""
    findings = []
    channel_usage = {}

    for ap in ap_data:
        name = ap.get("name", "unknown")
        for radio in ap.get("radios", []):
            band = radio.get("band", "?")
            channel = radio.get("channel", 0)
            width = radio.get("width", 20)
            tx_power = radio.get("tx_power", 0)
            clients = radio.get("client_count", 0)

            key = f"{band}:{channel}"
            if key not in channel_usage:
                channel_usage[key] = []
            channel_usage[key].append({"ap": name, "width": width, "power": tx_power, "clients": clients})

    # Check for co-channel interference
    for key, aps in channel_usage.items():
        if len(aps) > 1:
            findings.append({
                "type": "co_channel_interference",
                "severity": "medium",
                "detail": f"Channel {key}: {len(aps)} APs sharing — {', '.join(a['ap'] for a in aps)}",
                "category": "channel_assignment",
            })

    # Check for high-power in small space
    for ap in ap_data:
        for radio in ap.get("radios", []):
            if radio.get("tx_power", 0) > 20 and radio.get("band") == "2.4GHz":
                findings.append({
                    "type": "excessive_tx_power",
                    "severity": "low",
                    "detail": f"{ap['name']} 2.4GHz at {radio['tx_power']}dBm — may cause sticky clients",
                    "category": "power_management",
                })

    return findings


def generate_suggestions(findings):
    """Generate optimization suggestions (assisted mode only)."""
    suggestions = []
    for f in findings:
        if f["type"] == "co_channel_interference":
            suggestions.append({
                "finding": f["type"],
                "suggestion": "channel_reassignment",
                "detail": f["detail"],
                "auto_applicable": False,
                "mode": "assisted",
            })
        elif f["type"] == "excessive_tx_power":
            suggestions.append({
                "finding": f["type"],
                "suggestion": "power_adjustment",
                "detail": f["detail"],
                "auto_applicable": False,
                "mode": "assisted",
            })
    return suggestions


def run_audit(ap_data=None):
    """Run WiFi audit."""
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    if ap_data is None:
        ap_data = [
            {
                "name": "U7-Pro-XG",
                "model": "UniFi U7 Pro XG",
                "ip": "10.1.1.19",
                "radios": [
                    {"band": "2.4GHz", "channel": 6, "width": 20, "tx_power": 15, "client_count": 3},
                    {"band": "5GHz", "channel": 36, "width": 80, "tx_power": 20, "client_count": 5},
                    {"band": "6GHz", "channel": 1, "width": 160, "tx_power": 23, "client_count": 0},
                ],
            }
        ]

    findings = analyze_channels(ap_data)
    suggestions = generate_suggestions(findings)

    ts = datetime.now(timezone.utc)
    report = {
        "report_type": "wifi_audit",
        "timestamp": ts.isoformat(),
        "mode": "assisted",
        "ap_count": len(ap_data),
        "finding_count": len(findings),
        "findings": findings,
        "suggestions": suggestions,
    }

    out_file = AUDIT_DIR / f"wifi_audit_{ts.strftime('%Y%m%d_%H%M%S')}.json"
    with open(out_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"[OK] WiFi audit: {out_file.name}")
    print(f"     APs: {len(ap_data)}, Findings: {len(findings)}, Suggestions: {len(suggestions)}")
    return report


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "audit"
    if cmd == "audit":
        run_audit()
    else:
        print("Usage: wifi_optimizer.py [audit]")


if __name__ == "__main__":
    main()
