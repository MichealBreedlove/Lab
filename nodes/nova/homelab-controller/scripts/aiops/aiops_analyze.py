#!/usr/bin/env python3
"""P34 — AIOps Analyzer: use Ollama LLM to analyze cluster state and generate insights."""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = ROOT / "artifacts" / "aiops"
CAPACITY_DIR = ROOT / "artifacts" / "capacity"
DR_DIR = ROOT / "artifacts" / "dr"
CONFIG_DIR = ROOT / "config"

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


def load_json_safe(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def build_context():
    """Build a context string from all available artifacts."""
    sections = []

    # Capacity
    capacity = load_json_safe(CAPACITY_DIR / "latest.json")
    if capacity:
        sections.append("## Current Capacity Metrics")
        for node, data in capacity.get("nodes", {}).items():
            if data.get("status") == "ok":
                sections.append(f"- {node}: CPU {data.get('cpu_pct')}%, Mem {data.get('memory_pct')}%, Disk {data.get('disk_pct')}%, Load {data.get('load_ratio')}x")
            elif data.get("status") == "skipped":
                sections.append(f"- {node}: (Windows, skipped)")
        if capacity.get("alerts"):
            sections.append(f"\nAlerts: {json.dumps(capacity['alerts'], indent=2)}")

    # Forecast
    forecast = load_json_safe(CAPACITY_DIR / "forecast.json")
    if forecast and forecast.get("alerts"):
        sections.append("\n## Capacity Forecasts")
        for a in forecast["alerts"]:
            sections.append(f"- {a['node']}/{a['metric']}: {a['days_until_full']}d until full ({a['level']})")

    # DR
    dr = load_json_safe(DR_DIR / "dr_status.json")
    if dr:
        sections.append(f"\n## DR Status: {dr.get('status')} (score: {dr.get('readiness_score')})")
        if dr.get("last_drill_mttr_sec"):
            sections.append(f"Last drill MTTR: {dr['last_drill_mttr_sec']}s")

    # Anomalies
    anomalies = load_json_safe(ARTIFACTS_DIR / "anomalies.json")
    if anomalies and anomalies.get("anomalies"):
        sections.append("\n## Anomalies Detected")
        for a in anomalies["anomalies"]:
            sections.append(f"- {a['node']}/{a['metric']}: z-score {a['z_score']} ({a['direction']})")

    # Correlations
    correlations = load_json_safe(ARTIFACTS_DIR / "correlations.json")
    if correlations and correlations.get("incidents"):
        sections.append("\n## Correlated Incidents")
        for inc in correlations["incidents"]:
            sections.append(f"- {inc['type']}: {json.dumps(inc)}")

    return "\n".join(sections) if sections else "No data available."


def query_ollama(prompt, config):
    """Send analysis request to Ollama."""
    if not HAS_REQUESTS:
        return {"error": "requests library not installed", "suggestion": "pip3 install requests"}

    endpoint = config.get("endpoint", "http://10.1.1.150:11434")
    model = config.get("model", "llama3.1:8b")
    timeout = config.get("timeout_sec", 60)

    try:
        resp = requests.post(
            f"{endpoint}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": config.get("max_tokens", 2048)},
            },
            timeout=timeout,
        )
        if resp.status_code == 200:
            return {"ok": True, "response": resp.json().get("response", "")}
        return {"ok": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}
    except requests.exceptions.ConnectionError:
        return {"ok": False, "error": f"Cannot connect to Ollama at {endpoint}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def run_analysis(use_llm=True):
    policy = load_json_safe(CONFIG_DIR / "aiops_policy.json") or {}
    ollama_cfg = policy.get("ollama", {})
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    context = build_context()

    result = {
        "timestamp": timestamp,
        "context_length": len(context),
        "llm_used": False,
        "analysis": None,
        "recommendations": [],
    }

    if use_llm and policy.get("enabled"):
        prompt = f"""You are an SRE operations analyst for a 4-node homelab cluster (nova, mira, orin, jasper).
Analyze the following cluster state and provide:
1. A brief health summary (1-2 sentences)
2. Top 3 concerns ranked by severity
3. Specific actionable recommendations

Cluster State:
{context}

Respond in structured format with clear sections."""

        llm_result = query_ollama(prompt, ollama_cfg)
        if llm_result.get("ok"):
            result["llm_used"] = True
            result["analysis"] = llm_result["response"]
        else:
            result["llm_error"] = llm_result.get("error")

    # Fallback: rule-based analysis
    if not result["analysis"]:
        result["analysis"] = f"Rule-based analysis (LLM not available):\n{context}"

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(ARTIFACTS_DIR / "analysis.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


def main():
    parser = argparse.ArgumentParser(description="AIOps Analyzer")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM, use rule-based only")
    args = parser.parse_args()

    result = run_analysis(use_llm=not args.no_llm)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        llm_tag = "🤖 LLM" if result["llm_used"] else "📋 Rule-based"
        print(f"🧠 AIOps Analysis ({llm_tag})")
        print(f"{'─' * 50}")
        print(result.get("analysis", "No analysis available"))
        if result.get("llm_error"):
            print(f"\n⚠️  LLM error: {result['llm_error']}")

    sys.exit(0)


if __name__ == "__main__":
    main()
