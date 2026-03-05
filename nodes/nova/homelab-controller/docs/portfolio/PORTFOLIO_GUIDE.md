# Portfolio Export Guide — P39

## What It Does

Generates a recruiter-ready portfolio bundle from live subsystem artifacts. One command produces a clean `_meta/` directory with architecture docs, capability maps, operational summaries, and status badges.

## Quick Commands

```bash
oc portfolio render    # Generate all portfolio docs
oc portfolio status    # Check export status
oc portfolio tick      # Full pipeline (render + scan + status)
oc portfolio test      # Run acceptance tests
```

## Generated Documents

| File | Content |
|------|---------|
| `_meta/PORTFOLIO_README.md` | Top-level narrative + architecture table |
| `_meta/CAPABILITIES.md` | Full capability map (all subsystems) |
| `_meta/OPERATIONS.md` | DR/capacity operational summaries |
| `_meta/SECURITY.md` | Security audit + scan results |
| `_meta/BADGES.md` | Auto-generated status badges |

## How It Works

1. `portfolio_render.py` reads artifacts from all subsystems (DR, capacity, security, etc.)
2. Generates clean markdown with no secrets or internal paths
3. `portfolio_badges.py` creates shields.io badge markdown from dashboard status JSONs
4. `portfolio_tick.sh` runs render → secret scan → status publish
5. Dashboard shows last export time and doc count

## Adding New Docs

Add a new render function in `portfolio_render.py` and include it in `render_all()`. The function should:
- Read from `artifacts/` directories
- Output clean markdown (no secrets, no absolute paths)
- Write to `_meta/` in the Lab repo root

## Security

- All output is scanned before commit
- No credentials or internal IPs in exported docs
- Redaction library (`sec_redact.py`) available for custom content
