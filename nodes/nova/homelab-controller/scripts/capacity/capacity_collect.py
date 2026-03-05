#!/usr/bin/env python3
"""P32 — Capacity Collector: gather CPU, memory, disk, load metrics from all nodes via SSH."""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "artifacts" / "capacity"
CONFIG_DIR = ROOT / "config"


def load_json(path):
    with open(path) as f:
        return json.load(f)


def ssh_cmd(host, user, key_path, command, timeout=30):
    key_path = str(Path(key_path).expanduser())
    try:
        r = subprocess.run(
            ["ssh", "-o", "StrictHostKeyChecking=accept-new",
             "-o", "ConnectTimeout=10",
             "-i", key_path,
             f"{user}@{host}", command],
            capture_output=True, text=True, timeout=timeout
        )
        return {"ok": r.returncode == 0, "stdout": r.stdout.strip()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def collect_linux(ip, user, key):
    """Collect metrics from a Linux node."""
    metrics = {}

    # CPU usage (1-second sample)
    r = ssh_cmd(ip, user, key, "top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1")
    if r["ok"]:
        try:
            metrics["cpu_pct"] = round(float(r["stdout"]), 1)
        except ValueError:
            metrics["cpu_pct"] = None
    else:
        metrics["cpu_pct"] = None

    # Memory
    r = ssh_cmd(ip, user, key, "free -b | awk '/Mem:/ {printf \"%d %d %d\", $2, $3, $7}'")
    if r["ok"]:
        parts = r["stdout"].split()
        if len(parts) >= 3:
            total = int(parts[0])
            used = int(parts[1])
            avail = int(parts[2])
            metrics["memory_total_gb"] = round(total / (1024**3), 1)
            metrics["memory_used_gb"] = round(used / (1024**3), 1)
            metrics["memory_avail_gb"] = round(avail / (1024**3), 1)
            metrics["memory_pct"] = round((used / total) * 100, 1) if total > 0 else None

    # Disk (root filesystem)
    r = ssh_cmd(ip, user, key, "df -B1 / | awk 'NR==2 {printf \"%d %d %d\", $2, $3, $4}'")
    if r["ok"]:
        parts = r["stdout"].split()
        if len(parts) >= 3:
            total = int(parts[0])
            used = int(parts[1])
            avail = int(parts[2])
            metrics["disk_total_gb"] = round(total / (1024**3), 1)
            metrics["disk_used_gb"] = round(used / (1024**3), 1)
            metrics["disk_avail_gb"] = round(avail / (1024**3), 1)
            metrics["disk_pct"] = round((used / total) * 100, 1) if total > 0 else None

    # Load average
    r = ssh_cmd(ip, user, key, "cat /proc/loadavg | awk '{print $1, $2, $3}'")
    if r["ok"]:
        parts = r["stdout"].split()
        if len(parts) >= 3:
            metrics["load_1m"] = float(parts[0])
            metrics["load_5m"] = float(parts[1])
            metrics["load_15m"] = float(parts[2])

    # CPU count
    r = ssh_cmd(ip, user, key, "nproc")
    if r["ok"]:
        metrics["cpu_cores"] = int(r["stdout"])
        if metrics.get("load_1m") is not None:
            metrics["load_ratio"] = round(metrics["load_1m"] / metrics["cpu_cores"], 2)

    # Uptime
    r = ssh_cmd(ip, user, key, "uptime -s")
    if r["ok"]:
        metrics["uptime_since"] = r["stdout"]

    return metrics


def collect_all():
    policy = load_json(CONFIG_DIR / "capacity_policy.json")
    profiles = load_json(CONFIG_DIR / "node_profiles.json")
    user = policy.get("ssh_user", "micheal")
    key = policy.get("ssh_key_path", "~/.ssh/id_ed25519")
    thresholds = policy.get("thresholds", {})

    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    results = {"timestamp": timestamp, "nodes": {}, "alerts": []}

    for node_name, node_cfg in profiles.get("nodes", {}).items():
        if node_cfg.get("platform") != "linux":
            results["nodes"][node_name] = {
                "status": "skipped",
                "reason": f"platform={node_cfg.get('platform')} (only Linux supported)",
            }
            continue

        ip = node_cfg["ip"]
        metrics = collect_linux(ip, user, key)
        metrics["node"] = node_name
        metrics["ip"] = ip
        metrics["profile"] = node_cfg.get("profile", "unknown")
        metrics["timestamp"] = timestamp
        metrics["status"] = "ok" if metrics.get("cpu_pct") is not None else "error"

        # Check thresholds
        alerts = []
        if metrics.get("cpu_pct") is not None and metrics["cpu_pct"] >= thresholds.get("cpu_crit_pct", 95):
            alerts.append({"level": "critical", "metric": "cpu", "value": metrics["cpu_pct"], "threshold": thresholds["cpu_crit_pct"]})
        elif metrics.get("cpu_pct") is not None and metrics["cpu_pct"] >= thresholds.get("cpu_warn_pct", 80):
            alerts.append({"level": "warning", "metric": "cpu", "value": metrics["cpu_pct"], "threshold": thresholds["cpu_warn_pct"]})

        if metrics.get("memory_pct") is not None and metrics["memory_pct"] >= thresholds.get("memory_crit_pct", 95):
            alerts.append({"level": "critical", "metric": "memory", "value": metrics["memory_pct"], "threshold": thresholds["memory_crit_pct"]})
        elif metrics.get("memory_pct") is not None and metrics["memory_pct"] >= thresholds.get("memory_warn_pct", 80):
            alerts.append({"level": "warning", "metric": "memory", "value": metrics["memory_pct"], "threshold": thresholds["memory_warn_pct"]})

        if metrics.get("disk_pct") is not None and metrics["disk_pct"] >= thresholds.get("disk_crit_pct", 90):
            alerts.append({"level": "critical", "metric": "disk", "value": metrics["disk_pct"], "threshold": thresholds["disk_crit_pct"]})
        elif metrics.get("disk_pct") is not None and metrics["disk_pct"] >= thresholds.get("disk_warn_pct", 80):
            alerts.append({"level": "warning", "metric": "disk", "value": metrics["disk_pct"], "threshold": thresholds["disk_warn_pct"]})

        if metrics.get("load_ratio") is not None and metrics["load_ratio"] >= thresholds.get("load_crit_ratio", 4.0):
            alerts.append({"level": "critical", "metric": "load", "value": metrics["load_ratio"], "threshold": thresholds["load_crit_ratio"]})
        elif metrics.get("load_ratio") is not None and metrics["load_ratio"] >= thresholds.get("load_warn_ratio", 2.0):
            alerts.append({"level": "warning", "metric": "load", "value": metrics["load_ratio"], "threshold": thresholds["load_warn_ratio"]})

        metrics["alerts"] = alerts
        results["nodes"][node_name] = metrics
        results["alerts"].extend([{**a, "node": node_name} for a in alerts])

    # Write artifacts
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(ARTIFACTS_DIR / "latest.json", "w") as f:
        json.dump(results, f, indent=2)

    # Append to history
    history_file = ARTIFACTS_DIR / "history.jsonl"
    with open(history_file, "a") as f:
        f.write(json.dumps({"timestamp": timestamp, "nodes": {
            n: {"cpu": d.get("cpu_pct"), "mem": d.get("memory_pct"), "disk": d.get("disk_pct"), "load": d.get("load_ratio")}
            for n, d in results["nodes"].items() if d.get("status") == "ok"
        }}) + "\n")

    return results


def main():
    parser = argparse.ArgumentParser(description="Capacity Collector")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    results = collect_all()

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"📊 Capacity snapshot: {results['timestamp']}")
        for name, data in results["nodes"].items():
            if data.get("status") == "skipped":
                print(f"  ⏭️  {name}: {data.get('reason')}")
                continue
            cpu = f"{data.get('cpu_pct', '?')}%"
            mem = f"{data.get('memory_pct', '?')}%"
            disk = f"{data.get('disk_pct', '?')}%"
            load = f"{data.get('load_ratio', '?')}x"
            icon = "🟢" if not data.get("alerts") else "🟡" if all(a["level"] == "warning" for a in data["alerts"]) else "🔴"
            print(f"  {icon} {name}: CPU {cpu} | Mem {mem} | Disk {disk} | Load {load}")
            for a in data.get("alerts", []):
                ai = "⚠️" if a["level"] == "warning" else "🚨"
                print(f"      {ai} {a['metric']}: {a['value']} >= {a['threshold']}")

        if not results["alerts"]:
            print("  ✅ All nodes within thresholds")

    sys.exit(0)


if __name__ == "__main__":
    main()
