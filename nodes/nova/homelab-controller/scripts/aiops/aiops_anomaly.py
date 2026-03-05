#!/usr/bin/env python3
"""P34 — AIOps Anomaly Detection: z-score based anomaly detection on capacity metrics."""

import argparse
import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "artifacts" / "aiops"
CAPACITY_DIR = ROOT / "artifacts" / "capacity"
CONFIG_DIR = ROOT / "config"


def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def load_history():
    """Load capacity history for anomaly detection."""
    history_file = CAPACITY_DIR / "history.jsonl"
    if not history_file.exists():
        return {}

    series = {}
    for line in history_file.read_text().splitlines():
        try:
            entry = json.loads(line.strip())
        except json.JSONDecodeError:
            continue
        for node, metrics in entry.get("nodes", {}).items():
            if node not in series:
                series[node] = []
            series[node].append(metrics)
    return series


def compute_stats(values):
    """Compute mean and standard deviation."""
    n = len(values)
    if n < 2:
        return None, None
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / (n - 1)
    std = math.sqrt(variance)
    return mean, std


def detect_anomalies():
    policy = load_json(CONFIG_DIR / "aiops_policy.json") or {}
    anomaly_cfg = policy.get("anomaly_detection", {})
    z_threshold = anomaly_cfg.get("z_score_threshold", 3.0)
    min_samples = anomaly_cfg.get("min_samples", 10)
    metrics_to_check = anomaly_cfg.get("metrics", ["cpu_pct", "memory_pct", "disk_pct", "load_ratio"])

    history = load_history()
    latest = load_json(CAPACITY_DIR / "latest.json")
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    anomalies = []

    for node_name, data_points in history.items():
        if len(data_points) < min_samples:
            continue

        # Get latest values
        current = {}
        if latest:
            node_latest = latest.get("nodes", {}).get(node_name, {})
            # Map short names to full names
            metric_map = {"cpu": "cpu_pct", "mem": "memory_pct", "disk": "disk_pct", "load": "load_ratio"}
            for short, full in metric_map.items():
                if node_latest.get(full) is not None:
                    current[full] = node_latest[full]

        for metric in metrics_to_check:
            # Get historical values for this metric
            short_name = {"cpu_pct": "cpu", "memory_pct": "mem", "disk_pct": "disk", "load_ratio": "load"}.get(metric, metric)
            values = [dp.get(short_name) for dp in data_points if dp.get(short_name) is not None]

            if len(values) < min_samples:
                continue

            mean, std = compute_stats(values)
            if mean is None or std is None or std == 0:
                continue

            current_val = current.get(metric)
            if current_val is None:
                continue

            z_score = abs(current_val - mean) / std

            if z_score >= z_threshold:
                anomalies.append({
                    "node": node_name,
                    "metric": metric,
                    "current_value": current_val,
                    "mean": round(mean, 2),
                    "std": round(std, 2),
                    "z_score": round(z_score, 2),
                    "threshold": z_threshold,
                    "direction": "high" if current_val > mean else "low",
                    "severity": "critical" if z_score >= z_threshold * 1.5 else "warning",
                })

    result = {
        "timestamp": timestamp,
        "anomalies": anomalies,
        "nodes_analyzed": len(history),
        "config": {"z_threshold": z_threshold, "min_samples": min_samples},
    }

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(ARTIFACTS_DIR / "anomalies.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


def main():
    parser = argparse.ArgumentParser(description="AIOps Anomaly Detection")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = detect_anomalies()

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        if result["anomalies"]:
            print(f"🚨 {len(result['anomalies'])} anomalies detected:")
            for a in result["anomalies"]:
                print(f"  ⚠️  {a['node']}/{a['metric']}: {a['current_value']} (z={a['z_score']}, mean={a['mean']}±{a['std']})")
        else:
            print(f"✅ No anomalies detected ({result['nodes_analyzed']} nodes analyzed)")

    sys.exit(0)


if __name__ == "__main__":
    main()
