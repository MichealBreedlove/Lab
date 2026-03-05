# Credentials Policy

## Rules
1. **No secrets in this repo. Ever.**
2. API keys, tokens, and passwords are stored in each node's local `.env` or credential store — never committed.
3. SSH keys: private keys stay on the node. Only the public key fingerprint may be documented.
4. OpenClaw auth profiles: stored locally at `~/.openclaw/auth-profiles.json` — never committed.

## Where Secrets Live
| Secret Type | Location | Backed Up? |
|-------------|----------|------------|
| SSH private key | `~/.ssh/id_ed25519_homelab` | NO (regenerate) |
| OpenClaw auth | `~/.openclaw/auth-profiles.json` | NO (re-pair) |
| Ollama API keys | Environment variable | NO (re-set) |
| GitHub token | `gh auth` credential store | NO (re-auth) |

## If You Accidentally Commit a Secret
1. Rotate the credential immediately
2. Remove from git history: `git filter-branch` or `bfg`
3. Force push
4. Verify the GitHub Actions secret scan passes
