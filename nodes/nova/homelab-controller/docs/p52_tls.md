# P52 — TLS / Reverse Proxy Hardening

## Overview

The Platform API runs on port 8081 (HTTP). A Caddy reverse proxy fronts it with HTTPS using internal (self-signed) TLS certificates, accessible at `https://api.homelab.local`.

## Setup

### 1. Install Caddy on Nova

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install caddy
```

### 2. Configure DNS / Hosts

Add to `/etc/hosts` on all clients:
```
10.1.1.21  api.homelab.local
```

### 3. Deploy Caddyfile

```bash
sudo cp deploy/caddy/Caddyfile /etc/caddy/Caddyfile
sudo systemctl restart caddy
```

### 4. Verify

```bash
curl -k https://api.homelab.local/health
# Returns: OK

curl -k -H "Authorization: Bearer <token>" https://api.homelab.local/
# Returns: API status JSON
```

## Architecture

```
Client (LAN)
  |
  v
Caddy (port 443, TLS internal)
  |
  v
Platform API (port 8081, HTTP, localhost)
```

## Security Notes

- `tls internal` generates a self-signed CA certificate (Caddy auto)
- Clients on LAN need to trust the Caddy root CA or use `-k` flag
- Authorization header is forwarded unchanged to backend
- X-Real-IP and X-Forwarded-For headers added for audit logging
- Access log at `/var/log/caddy/api-access.log` (JSON format)

## Environment Variables

None required. The Caddyfile uses hardcoded internal addresses only.
