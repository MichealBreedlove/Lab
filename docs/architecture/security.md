# Security Practices

## Credential Management

- No credentials stored in the repository
- All secrets managed via environment variables or local policy files
- Credential policy documented in `inventory/creds_policy.md`

## Secret Scanning

GitHub Actions CI gate scans every commit for 11 patterns:

- AWS Access Keys (`AKIA...`)
- GitHub Personal Access Tokens (`ghp_...`)
- Private Keys (`-----BEGIN.*PRIVATE KEY-----`)
- OpenAI API Keys (`sk-...`)
- Generic tokens and database URIs
- 6 additional patterns

Zero credential leaks since deployment.

## Network Segmentation

VLANs isolate traffic by function:

| VLAN | Purpose | Example Devices |
|---|---|---|
| Infrastructure | Lab nodes, storage, management | Jasper, Nova, Mira, Orin |
| IoT | Smart home devices | Ring, Alexa, thermostat |
| Personal | Phones, TVs, streaming | Personal devices |

## Access Control

- SSH key authentication only (Ed25519)
- No password-based SSH access
- Per-node credential isolation
- Least-privilege principle applied to all service accounts

## Data Sanitization

Pre-commit sanitization scripts run on every node before data enters version control:

- Strip API keys and tokens
- Remove private key material
- Genericize internal hostnames where needed
- Redact file paths containing usernames

## Monitoring

- Service health checks on all critical endpoints
- SLO-driven alerting for degradation detection
- Incident tracking with automated escalation
