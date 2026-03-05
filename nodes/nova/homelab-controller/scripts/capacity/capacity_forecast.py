#!/usr/bin/env python3
"""P32 — Capacity Forecaster: linear trend analysis on collected metrics to predict exhaustion."""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "artifacts" / "capacity"
CONFIG_DIR = ROOT / "config"


def load_json(path):
    with open(path) as f:
        return json.load(f)


def load_history(days=30):
    """Load JSONL history and return per-node time series."""
    history_file = ARTIFACTS_DIR / "history.jsonl"
    if not history_file.exists():
        return {}

    cutoff = time.time() - (days * 86400)
    series = {}

    for line in history_file.read_text().splitlines():
        try:
            entry = json.loads(line.strip())
        except json.JSONDecodeError:
            continue

        ts_str = entry.get("timestamp", "")
        try:
            ts = time.mktime(time.strptime(ts_str[:19], "%Y-%m-%dT%H:%M:%S"))
        except (ValueError, TypeError):
            continue

        if ts < cutoff:
            continue

        for node_name, metrics in entry.get("nodes", {}).items():
            if node_name not in series:
                series[node_name] = []
            series[node_name].append({"ts": ts, **metrics})

    return series


def linear_regression(points):
    """Simple least-squares linear regression. Returns slope, intercept."""
    n = len(points)
    if n < 2:
        return 0, 0
    x = [p[0] for p in points]
    y = [p[1] for p in points]
    x_mean = sum(x) / n
    y_mean = sum(y) / n
    numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
    denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
    if denominator == 0:
        return 0, y_mean
    slope = numerator / denominator
    intercept = y_mean - slope * x_mean
    return slope, intercept


def forecast_metric(series, metric_key, target_pct=100):
    """Forecast when a metric will hit target_pct. Returns days or None."""
    points = [(s["ts"], s[metric_key]) for s in series if s.get(metric_key) is not None]
    if len(points) < 3:
        return None

    slope, intercept = linear_regression(points)
    if slope <= 0:
        return None  # Not growing

    current = points[-1][1]
    remaining = target_pct - current
    if remaining <= 0:
        return 0  # Already at/above target

    seconds_to_full = remaining / slope
    days_to_full = seconds_to_full / 86400
    return round(days_to_full, 1)


def run_forecast():
    policy = load_json(CONFIG_DIR / "capacity_policy.json")
    fc_cfg = policy.get("forecasting", {})
    history_days = fc_cfg.get("history_days", 30)
    warn_days = fc_cfg.get("warn_days_until_full", 30)
    crit_days = fc_cfg.get("crit_days_until_full", 7)

    series = load_history(history_days)
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    forecasts = {}
    alerts = []

    for node_name, data_points in series.items():
        node_forecast = {}
        for metric in ["disk", "mem"]:
            days = forecast_metric(data_points, metric, target_pct=100)
            node_forecast[metric] = {
                "days_until_full": days,
                "data_points": len(data_points),
                "status": "ok" if days is None or days > warn_days else "warning" if days > crit_days else "critical",
            }
            if days is not None and days <= warn_days:
                level = "critical" if days <= crit_days else "warning"
                alerts.append({
                    "node": node_name,
                    "metric": metric,
                    "days_until_full": days,
                    "level": level,
                })
        forecasts[node_name] = node_forecast

    result = {
        "timestamp": timestamp,
        "history_days": history_days,
        "forecasts": forecasts,
        "alerts": alerts,
    }

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(ARTIFACTS_DIR / "forecast.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


def main():
    parser = argparse.ArgumentParser(description="Capacity Forecaster")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = run_forecast()

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"📈 Capacity Forecast ({result['history_days']}d window)")
        for node, fc in result["forecasts"].items():
            print(f"  {node}:")
            for metric, data in fc.items():
                days = data["days_until_full"]
                icon = "🟢" if data["status"] == "ok" else "🟡" if data["status"] == "warning" else "🔴"
                print(f"    {icon} {metric}: {days if days is not None else '∞'}d to full ({data['data_points']} samples)")

        if result["alerts"]:
            print("\n  ⚠️  Alerts:")
            for a in result["alerts"]:
                print(f"    🚨 {a['node']}/{a['metric']}: {a['days_until_full']}d until full ({a['level']})")
        else:
            print("  ✅ No capacity concerns")

    sys.exit(0)


if __name__ == "__main__":
    main()
