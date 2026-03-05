#!/usr/bin/env python3
"""P41 — Supply Chain Status Publisher."""

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts" / "supply_chain"
DASHBOARD_DATA = ROOT / "dashboard" / "static" / "data"


def load_json_safe(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def publish():
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    sbom = load_json_safe(ARTIFACTS / "sbom.json")
    provenance = load_json_safe(ARTIFACTS / "provenance.json")
    hardening = load_json_safe(ARTIFACTS / "hardening_latest.json")

    sbom_ok = sbom.get("third_party_free", False) if sbom else False
    harden_ok = hardening.get("pass", False) if hardening else False
    prov_ok = provenance is not None

    all_ok = sbom_ok and harden_ok and prov_ok
    status = "GREEN" if all_ok else "YELLOW" if (sbom_ok or harden_ok) else "RED"

    result = {
        "timestamp": timestamp,
        "status": status,
        "sbom": {"components": sbom["metadata"]["component_count"] if sbom else 0, "third_party_free": sbom_ok},
        "hardening": {"pass": harden_ok, "files_checked": hardening.get("files_checked", 0) if hardening else 0},
        "provenance": {"recorded": prov_ok, "commit": provenance["git"]["commit"][:8] if provenance and provenance.get("git") else "?"},
    }

    DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)
    with open(DASHBOARD_DATA / "supply_status.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


if __name__ == "__main__":
    r = publish()
    icon = "🟢" if r["status"] == "GREEN" else "🟡" if r["status"] == "YELLOW" else "🔴"
    print(f"{icon} Supply Chain: {r['status']}")
    print(f"  SBOM: {r['sbom']['components']} components, 3rd-party free: {'✅' if r['sbom']['third_party_free'] else '❌'}")
    print(f"  Hardening: {'✅' if r['hardening']['pass'] else '❌'} ({r['hardening']['files_checked']} files)")
    print(f"  Provenance: {r['provenance']['commit']}")
