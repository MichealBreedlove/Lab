# Supply Chain & Hardening Guide — P41

## Quick Commands

```bash
oc supply status      # Supply chain health overview
oc supply sbom        # Generate SBOM
oc supply provenance  # Record build provenance
oc supply harden      # Run hardening checks
oc supply tick        # Full pipeline
oc supply test        # Run acceptance tests
```

## SBOM (Software Bill of Materials)

Generates `artifacts/supply_chain/sbom.json` containing:
- Every script and config file with SHA-256 hash
- Python import analysis (stdlib vs third-party classification)
- Component count and dependency summary

Currently: **zero third-party dependencies** — all Python stdlib.

## Provenance

Records `artifacts/supply_chain/provenance.json` with:
- Build environment (OS, Python version, hostname)
- Git state (commit, branch, dirty status, remote)
- Controller metadata (config count, script directories)

## Hardening Checks

Enforces script hygiene across all `.py` and `.sh` files:
- **Shebang enforcement**: All scripts must have proper `#!/usr/bin/env` lines
- **Bash safety**: All `.sh` scripts must use `set -euo pipefail`
- **Size limits**: Scripts must be under 100KB
- **Banned patterns**: No `curl | bash`, `wget | sh`, or `eval $(curl` patterns

## Dependency Pinning

- `config/requirements.txt` tracks Python dependencies
- Currently empty (stdlib-only) — pin versions here if third-party deps are added
- Supply chain policy enforces pinned versions

## Security Integration

- Secret scan runs as part of the supply chain tick
- Repo guard (P38) blocks commits with violations
- SBOM hashes enable integrity verification
