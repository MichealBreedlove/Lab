#!/usr/bin/env python3
"""P37 — Proxmox Config Export: safely export Proxmox cluster configs via SSH."""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "artifacts" / "infra" / "proxmox"
CONFIG_DIR = ROOT / "config"

REDACT_PATTERNS = [
    (re.compile(r'(password[=:\s]+)\S+', re.I), r'\1REDACTED'),
    (re.compile(r'(token[=:\s]+)\S+', re.I), r'\1REDACTED'),
    (re.compile(r'(secret[=:\s]+)\S+', re.I), r'\1REDACTED'),
]


def load_json(path):
    with open(path) as f:
        return json.load(f)


def ssh_cmd(host, user, key_path, command, timeout=30):
    key_path = str(Path(key_path).expanduser())
    try:
        r = subprocess.run(
            ["ssh", "-o", "StrictHostKeyChecking=accept-new", "-o", "ConnectTimeout=10",
             "-i", key_path, f"{user}@{host}", command],
            capture_output=True, text=True, timeout=timeout
        )
        return {"ok": r.returncode == 0, "stdout": r.stdout, "stderr": r.stderr.strip()[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def redact(text):
    for pattern, replacement in REDACT_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def export_proxmox():
    targets = load_json(CONFIG_DIR / "infra_targets.json")
    pve = targets.get("proxmox", {})
    export_paths = pve.get("export_paths", [])
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    results = {"timestamp": timestamp, "hosts": {}}

    for host_name, host_cfg in pve.get("hosts", {}).items():
        ip = host_cfg["ip"]
        user = host_cfg.get("ssh_user", "root")
        host_results = {"files": {}, "cluster_info": {}}

        # Export config files
        for path in export_paths:
            r = ssh_cmd(ip, user, "~/.ssh/id_ed25519", f"cat {path} 2>/dev/null")
            if r["ok"]:
                content = redact(r["stdout"])
                filename = path.replace("/", "_").lstrip("_")
                host_results["files"][path] = {"exported": True, "size": len(content)}

                ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
                (ARTIFACTS_DIR / f"{host_name}_{filename}").write_text(content)
            else:
                host_results["files"][path] = {"exported": False, "reason": r.get("stderr") or r.get("error", "unknown")}

        # Cluster status
        r = ssh_cmd(ip, user, "~/.ssh/id_ed25519", "pvecm status 2>/dev/null || echo 'not available'")
        if r["ok"]:
            host_results["cluster_info"]["status"] = redact(r["stdout"][:500])

        # Node list
        r = ssh_cmd(ip, user, "~/.ssh/id_ed25519", "pvecm nodes 2>/dev/null || echo 'not available'")
        if r["ok"]:
            host_results["cluster_info"]["nodes"] = redact(r["stdout"][:500])

        results["hosts"][host_name] = host_results

    # Write summary
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(ARTIFACTS_DIR / "export_summary.json", "w") as f:
        json.dump(results, f, indent=2)

    return results


def main():
    parser = argparse.ArgumentParser(description="Proxmox Config Export")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = export_proxmox()

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"📦 Proxmox Export ({result['timestamp'][:19]})")
        for host, data in result["hosts"].items():
            exported = sum(1 for f in data["files"].values() if f.get("exported"))
            total = len(data["files"])
            print(f"  🖥️  {host}: {exported}/{total} files exported")

    sys.exit(0)


if __name__ == "__main__":
    main()
