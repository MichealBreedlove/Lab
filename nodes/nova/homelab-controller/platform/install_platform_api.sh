#!/usr/bin/env bash
# Install Platform API as a systemd user service on Nova
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/.."
SYSTEMD_DIR="$HOME/.config/systemd/user"

mkdir -p "$SYSTEMD_DIR"

cat > "$SYSTEMD_DIR/homelab-platform-api.service" << EOF
[Unit]
Description=Homelab Platform API
After=network.target

[Service]
Type=simple
WorkingDirectory=$ROOT_DIR
ExecStart=/usr/bin/python3 $SCRIPT_DIR/api/server.py
Environment=PLATFORM_PORT=8081
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable homelab-platform-api.service
systemctl --user start homelab-platform-api.service

echo "[OK] Platform API service installed"
echo "  Port: 8081"
echo "  Status: systemctl --user status homelab-platform-api"
