#!/usr/bin/env python3
"""P39 — Portfolio Status Publisher."""

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_DATA = ROOT / "dashboard" / "static" / "data"
META_DIR = ROOT.parents[2] / "_meta"


def publish():
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    docs = list(META_DIR.glob("*.md")) if META_DIR.exists() else []

    result = {
        "timestamp": timestamp,
        "docs_count": len(docs),
        "docs": [f.name for f in docs],
        "status": "GREEN" if len(docs) >= 3 else "YELLOW" if len(docs) > 0 else "RED",
    }

    DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)
    with open(DASHBOARD_DATA / "portfolio_status.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


if __name__ == "__main__":
    r = publish()
    print(f"📦 Portfolio: {r['docs_count']} docs exported")
