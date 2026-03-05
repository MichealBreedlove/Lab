#!/usr/bin/env python3
"""P33 — Dependencies Docs: auto-generate dependency map from imports and configs."""

import argparse
import ast
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT / "docs" / "generated"
SCRIPTS_DIR = ROOT / "scripts"


def scan_python_imports(directory):
    """Scan Python files for imports, return dependency map."""
    deps = {}
    for py_file in directory.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        rel = str(py_file.relative_to(ROOT))
        imports = set()
        try:
            tree = ast.parse(py_file.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module.split(".")[0])
        except Exception:
            continue

        # Separate stdlib from third-party
        stdlib = {"os", "sys", "json", "time", "re", "pathlib", "argparse", "ast",
                  "subprocess", "socket", "importlib", "hashlib", "shutil", "datetime",
                  "collections", "functools", "itertools", "math", "typing", "io",
                  "tempfile", "glob", "copy", "string", "textwrap", "logging", "unittest"}
        third_party = imports - stdlib
        # Remove local modules
        local_modules = {p.stem for p in SCRIPTS_DIR.rglob("*.py")}
        third_party = third_party - local_modules - {""}

        if third_party:
            deps[rel] = sorted(third_party)

    return deps


def scan_config_deps():
    """Scan config files for cross-references."""
    config_dir = ROOT / "config"
    refs = {}
    for cfg_file in config_dir.glob("*.json"):
        try:
            data = json.loads(cfg_file.read_text())
            text = json.dumps(data)
            # Find references to other config files or scripts
            referenced = set()
            for other_cfg in config_dir.glob("*.json"):
                if other_cfg != cfg_file and other_cfg.stem in text:
                    referenced.add(str(other_cfg.relative_to(ROOT)))
            if referenced:
                refs[str(cfg_file.relative_to(ROOT))] = sorted(referenced)
        except Exception:
            continue
    return refs


def generate_dependencies():
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    python_deps = scan_python_imports(SCRIPTS_DIR)
    config_refs = scan_config_deps()

    # Collect all third-party packages
    all_packages = set()
    for pkgs in python_deps.values():
        all_packages.update(pkgs)

    lines = [
        "# Dependency Map",
        "",
        f"*Auto-generated: {timestamp}*",
        "",
        "## Third-Party Python Packages",
        "",
        "| Package | Used By |",
        "|---------|---------|",
    ]

    # Group by package
    pkg_users = {}
    for file, pkgs in python_deps.items():
        for pkg in pkgs:
            if pkg not in pkg_users:
                pkg_users[pkg] = []
            pkg_users[pkg].append(file)

    for pkg in sorted(pkg_users.keys()):
        users = ", ".join(f"`{u}`" for u in sorted(pkg_users[pkg]))
        lines.append(f"| {pkg} | {users} |")

    lines.extend([
        "",
        "## Config Cross-References",
        "",
    ])

    if config_refs:
        for cfg, refs in sorted(config_refs.items()):
            lines.append(f"- `{cfg}` → {', '.join(f'`{r}`' for r in refs)}")
    else:
        lines.append("*No cross-references found.*")

    lines.extend([
        "",
        "## Module Structure",
        "",
        "```",
        "scripts/",
    ])

    for subdir in sorted(SCRIPTS_DIR.iterdir()):
        if subdir.is_dir() and not subdir.name.startswith("__"):
            py_files = sorted(subdir.glob("*.py"))
            sh_files = sorted(subdir.glob("*.sh"))
            ps_files = sorted(subdir.glob("*.ps1"))
            all_files = py_files + sh_files + ps_files
            if all_files:
                lines.append(f"  {subdir.name}/")
                for f in all_files:
                    lines.append(f"    {f.name}")

    lines.append("```")
    lines.append("")

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "DEPENDENCIES.md").write_text("\n".join(lines))

    return {
        "file": "docs/generated/DEPENDENCIES.md",
        "third_party_packages": sorted(all_packages),
        "files_scanned": len(python_deps),
    }


def main():
    parser = argparse.ArgumentParser(description="Generate Dependency Docs")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = generate_dependencies()

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"📄 Generated: {result['file']}")
        print(f"  Third-party packages: {', '.join(result['third_party_packages']) or 'none'}")
        print(f"  Files scanned: {result['files_scanned']}")

    sys.exit(0)


if __name__ == "__main__":
    main()
