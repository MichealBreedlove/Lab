#!/usr/bin/env python3
"""P37 — OPNsense Backup: manage manual config export workflow."""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "artifacts" / "infra" / "opnsense"
CONFIG_DIR = ROOT / "config"


def load_json(path):
    with open(path) as f:
        return json.load(f)


def check_backup():
    """Check if manual backup exists and report freshness."""
    targets = load_json(CONFIG_DIR / "infra_targets.json")
    opn = targets.get("opnsense", {})
    backup_dir = ROOT.parents[2] / opn.get("backup_dir", "network/firewall/opnsense/config_backups")

    result = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host": opn.get("host", "10.1.1.1"),
        "method": opn.get("method", "manual-export"),
        "backup_dir": str(backup_dir),
        "backups": [],
    }

    if backup_dir.exists():
        for f in sorted(backup_dir.glob("*.xml"), reverse=True):
            age_hours = (time.time() - f.stat().st_mtime) / 3600
            result["backups"].append({
                "file": f.name,
                "size_kb": round(f.stat().st_size / 1024, 1),
                "age_hours": round(age_hours, 1),
                "fresh": age_hours < 168,  # Less than 1 week
            })

    result["has_backup"] = len(result["backups"]) > 0
    result["latest_fresh"] = result["backups"][0]["fresh"] if result["backups"] else False

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(ARTIFACTS_DIR / "backup_status.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


def main():
    parser = argparse.ArgumentParser(description="OPNsense Backup Manager")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = check_backup()

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["has_backup"]:
            latest = result["backups"][0]
            icon = "✅" if latest["fresh"] else "⚠️"
            print(f"{icon} OPNsense backup: {latest['file']} ({latest['age_hours']}h old, {latest['size_kb']}KB)")
        else:
            print("❌ No OPNsense backup found")
            print(f"\n📋 Manual export instructions:")
            print(f"  1. Open https://{result['host']}/ in browser")
            print(f"  2. Go to System > Configuration > Backups")
            print(f"  3. Click 'Download configuration'")
            print(f"  4. Save to: {result['backup_dir']}/")

    sys.exit(0)


if __name__ == "__main__":
    main()
