#!/usr/bin/env python3
"""D6 — DR Validate: verifies restore success (services, ports, connectivity)."""

import argparse
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "artifacts" / "dr"
CONFIG_DIR = ROOT / "config"


def load_json(path):
    with open(path) as f:
        return json.load(f)


def check_port(host, port, timeout=5):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        result = s.connect_ex((host, port))
        s.close()
        return result == 0
    except Exception:
        return False


def check_service(name):
    try:
        r = subprocess.run(
            ["systemctl", "--user", "is-active", name],
            capture_output=True, text=True, timeout=10
        )
        return r.stdout.strip() == "active"
    except Exception:
        return False


def check_file_exists(path):
    return Path(path).expanduser().exists()


def validate_node(node):
    targets = load_json(CONFIG_DIR / "restore_targets.json")
    node_cfg = targets["nodes"].get(node)
    if not node_cfg:
        return {"error": f"node {node} not found", "pass": False}

    results = {
        "node": node,
        "platform": node_cfg["platform"],
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "checks": [],
    }

    for comp_name, comp in node_cfg.get("components", {}).items():
        validate = comp.get("validate", {})

        # Port checks
        for port in validate.get("ports", []):
            ok = check_port("127.0.0.1", port)
            results["checks"].append({
                "component": comp_name,
                "type": "port",
                "target": port,
                "pass": ok,
                "detail": f"port {port} {'open' if ok else 'closed'}",
            })

        # Service checks
        for svc in validate.get("services", []):
            ok = check_service(svc)
            results["checks"].append({
                "component": comp_name,
                "type": "service",
                "target": svc,
                "pass": ok,
                "detail": f"service {svc} {'active' if ok else 'inactive'}",
            })

        # File checks
        for fp in validate.get("files", []):
            ok = check_file_exists(fp)
            results["checks"].append({
                "component": comp_name,
                "type": "file",
                "target": fp,
                "pass": ok,
                "detail": f"file {fp} {'exists' if ok else 'missing'}",
            })

        # Task checks (Windows)
        for task in validate.get("tasks", []):
            try:
                r = subprocess.run(
                    ["schtasks", "/query", "/tn", task], capture_output=True, text=True, timeout=10
                )
                ok = r.returncode == 0
            except Exception:
                ok = False
            results["checks"].append({
                "component": comp_name,
                "type": "task",
                "target": task,
                "pass": ok,
                "detail": f"task {task} {'found' if ok else 'missing'}",
            })

    # Cross-node connectivity
    node_ports = {"jasper": 18789, "nova": 18789, "mira": 18789, "orin": 18789}
    node_ips = {"jasper": "10.1.1.150", "nova": "10.1.1.21", "mira": "10.1.1.22", "orin": "10.1.1.23"}

    for remote_name, remote_ip in node_ips.items():
        if remote_name == node:
            continue
        port = node_ports.get(remote_name, 18789)
        ok = check_port(remote_ip, port, timeout=3)
        results["checks"].append({
            "component": "cluster",
            "type": "connectivity",
            "target": f"{remote_name}:{port}",
            "pass": ok,
            "detail": f"{remote_name} ({remote_ip}:{port}) {'reachable' if ok else 'unreachable'}",
        })

    # Summary
    total = len(results["checks"])
    passing = sum(1 for c in results["checks"] if c["pass"])
    results["summary"] = {
        "total": total,
        "passing": passing,
        "failing": total - passing,
        "pass_rate": round(passing / total * 100, 1) if total > 0 else 0,
    }
    results["pass"] = results["summary"]["failing"] == 0

    # Write artifact
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(ARTIFACTS_DIR / f"validate_{node}.json", "w") as f:
        json.dump(results, f, indent=2)

    return results


def main():
    parser = argparse.ArgumentParser(description="DR Validate")
    parser.add_argument("--node", help="Target node (auto-detect if omitted)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    node = args.node
    if not node:
        hostname = socket.gethostname().lower()
        for n in ["jasper", "nova", "mira", "orin"]:
            if n in hostname:
                node = n
                break
        if not node:
            node = hostname

    result = validate_node(node)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        s = result.get("summary", {})
        icon = "✅" if result.get("pass") else "❌"
        print(f"{icon} Validate: {s.get('passing')}/{s.get('total')} checks passing")
        for c in result.get("checks", []):
            ci = "✅" if c["pass"] else "❌"
            print(f"  {ci} [{c['component']}] {c['detail']}")

    sys.exit(0 if result.get("pass") else 1)


if __name__ == "__main__":
    main()
