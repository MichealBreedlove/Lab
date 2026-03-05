# Security Model — P38

## Access Model

| Role | Node | Access Method | Permissions |
|------|------|---------------|-------------|
| Operator | Jasper (Windows) | Local + SSH | Full admin |
| Controller | Nova (Linux) | SSH key auth | Automation, backups, exports |
| Worker | Mira/Orin (Linux) | SSH key auth | Execute tasks |
| Infrastructure | OPNsense/Proxmox | Web UI + SSH | Network/VM management |

## Key Principles

1. **SSH key-only authentication** — no password auth on Linux nodes
2. **No secrets in git** — all commits scanned before push
3. **Redaction before export** — shared library ensures consistent secret removal
4. **Least privilege** — workers can't modify controller configs
5. **Break-glass for destructive ops** — time-limited tokens required

## SSH Key Management

- Primary key: `~/.ssh/id_ed25519`
- All Linux nodes accept this key for user `micheal`
- Root SSH only for Proxmox nodes (infrastructure management)

## Secret Scanning

- Built-in scanner checks for: AWS keys, GitHub tokens, OpenAI keys, private keys, passwords
- Runs before every git push via `sec_secretscan.py`
- Violations block the push

## Baseline Audit Checks

- SSH daemon configuration (PermitRootLogin, PasswordAuthentication)
- Firewall status
- Open port count
- NOPASSWD sudoers entries
- Weak services disabled (telnet, ftp, rsh, rlogin)

## CLI Commands

```bash
oc sec status    # Security status overview
oc sec audit     # Run baseline audit on all nodes
oc sec scan      # Run secret scanner
oc sec tick      # Full security pipeline
oc sec test      # Run acceptance tests
```
