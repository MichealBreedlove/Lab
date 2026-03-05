# Security Policy

## Never Commit
- API keys, tokens, cookies, private keys
- `auth-profiles.json`, `.env`, anything with `sk-`, `token`, `bearer`, etc.
- SSH private keys, PEM files, certificates
- Session data, cookies, credentials of any kind

## All Exports Must Be Sanitized First
Before committing any config or state export from a node, run it through the sanitize script:
```bash
bash tools/backup/linux/lab-sanitize.sh <file>
```

## Reporting Security Issues
If you find committed secrets:
1. Immediately rotate the affected credential
2. Use `git filter-branch` or `bfg` to remove from history
3. Force-push the cleaned history

## GitHub Actions Gate
The `verify-no-secrets.yml` workflow runs on every push and will **fail** if it detects:
- `sk-` prefixed strings
- `Authorization: Bearer`
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`
- `-----BEGIN PRIVATE KEY-----`
- Other common secret patterns
