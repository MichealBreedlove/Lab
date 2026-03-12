# Automation Tools

Tooling used for AI agent operations, security enforcement, and daily cluster management.

---

## Semantic Memory Search (memsearch)

**Purpose:** Semantic search across Jasper's AI agent memory files using local vector embeddings — no cloud dependency.

**Usage:**
```bash
python3 scripts/memory_search.py search '<query>'
python3 scripts/memory_search.py index
python3 scripts/memory_search.py stats
```

| Property | Value |
|---|---|
| Backend | ChromaDB + nomic-embed-text (Ollama) |
| Database | `C:\Users\mikej\.memsearch\chroma\` |
| Embedding model | `nomic-embed-text` (local, fully offline) |
| Scope | Jasper AI agent memory files |

**Behavior:**
- Skips per-node raw log files (`*-nova.md`, `*-mira.md`, etc.)
- Skips files larger than 300 KB
- All inference runs locally via Ollama — no external API calls

---

## TruffleHog Secret Scanner

**Purpose:** Prevents secrets and credentials from being committed or pushed to the repository.

**Binary:** `C:\Users\mikej\tools\trufflehog.exe` (v3.93.8)

**Pre-push hook** — runs automatically on every `git push`:
```
C:\Users\mikej\Lab\.git\hooks\pre-push
```

**Manual scan:**
```powershell
trufflehog.exe git file://C:/Users/mikej/Lab --since-commit HEAD
```

**Integration:**
- Pre-push hook blocks the push if secrets are detected
- GitHub Actions workflow `verify-no-secrets.yml` provides a second gate on every push
- Works in conjunction with `tools/backup/linux/lab-sanitize.sh` for config exports

---

## Morning Brief (PowerShell)

**Purpose:** Daily automated cluster health summary delivered to Jasper at 8:00 AM.

**Script:** `scripts/morning_brief.ps1`

**Scheduled task:** `Jasper-MorningBrief` — runs daily at 08:00

**Log:** `memory/morning-briefs.log`

**Coverage:**

| Area | Details |
|---|---|
| Cluster health | Prometheus targets up/down across all nodes |
| Active alerts | Firing alerts from Alertmanager |
| Task counts | Pending and active OpenClaw tasks |
| GPU status | RTX 4090 utilization and VRAM on Jasper |
| Disk usage | Free space across primary volumes |
| Weather | Local forecast via open-meteo API |

The brief is written to the morning-briefs log and surfaced to the Jasper agent context at session start.
