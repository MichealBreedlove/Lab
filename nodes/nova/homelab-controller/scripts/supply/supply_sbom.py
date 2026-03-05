#!/usr/bin/env python3
"""P41 — SBOM Generator: produce a software bill of materials for the controller."""

import ast
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "supply_chain_policy.json"
ARTIFACTS = ROOT / "artifacts" / "supply_chain"


def load_policy():
    with open(CONFIG) as f:
        return json.load(f)


def hash_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_imports(path):
    """Extract Python imports from a file."""
    try:
        tree = ast.parse(path.read_text())
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        return sorted(imports)
    except Exception:
        return []


def generate_sbom():
    policy = load_policy()
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    scan_dirs = policy["sbom"]["scan_dirs"]
    extensions = set(policy["sbom"]["include_extensions"])

    components = []
    all_imports = set()

    for scan_dir in scan_dirs:
        base = ROOT / scan_dir
        if not base.exists():
            continue
        for f in sorted(base.rglob("*")):
            if f.is_dir() or f.suffix not in extensions:
                continue
            if ".git" in f.parts or "__pycache__" in f.parts:
                continue

            component = {
                "name": str(f.relative_to(ROOT)),
                "type": f.suffix.lstrip("."),
                "size_bytes": f.stat().st_size,
                "sha256": hash_file(f),
            }

            if f.suffix == ".py":
                imports = extract_imports(f)
                component["imports"] = imports
                all_imports.update(imports)

            components.append(component)

    # Classify imports as stdlib vs third-party
    stdlib_modules = {
        "os", "sys", "json", "time", "re", "pathlib", "subprocess", "argparse",
        "hashlib", "ast", "importlib", "shutil", "tempfile", "datetime", "collections",
        "functools", "itertools", "typing", "io", "math", "random", "socket", "http",
        "urllib", "stat", "glob", "textwrap", "abc", "copy", "enum", "dataclasses",
    }
    third_party = sorted(all_imports - stdlib_modules - {"__future__"})
    internal_modules = sorted({i for i in all_imports if i.startswith(("scripts", "config"))})

    sbom = {
        "format": "cyclonedx-lite",
        "version": "1.0",
        "timestamp": timestamp,
        "metadata": {
            "tool": "homelab-controller/supply_sbom.py",
            "component_count": len(components),
        },
        "components": components,
        "dependencies": {
            "stdlib": sorted(all_imports & stdlib_modules),
            "third_party": third_party,
            "internal": internal_modules,
        },
        "third_party_free": len(third_party) == 0,
    }

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    with open(ARTIFACTS / "sbom.json", "w") as f:
        json.dump(sbom, f, indent=2)

    return sbom


if __name__ == "__main__":
    sbom = generate_sbom()
    print(f"📦 SBOM: {sbom['metadata']['component_count']} components")
    print(f"  stdlib deps: {len(sbom['dependencies']['stdlib'])}")
    print(f"  third-party: {len(sbom['dependencies']['third_party'])} {'✅' if sbom['third_party_free'] else '⚠️'}")
