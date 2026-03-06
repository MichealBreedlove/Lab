#!/usr/bin/env bash
# Install node_exporter on a remote Linux node via SSH
# Usage: install_node_exporter.sh <user>@<host>
set -euo pipefail

TARGET="${1:?Usage: install_node_exporter.sh user@host}"
NE_VERSION="1.7.0"
NE_URL="https://github.com/prometheus/node_exporter/releases/download/v${NE_VERSION}/node_exporter-${NE_VERSION}.linux-amd64.tar.gz"

echo "Installing node_exporter on $TARGET..."

ssh "$TARGET" bash -s << 'REMOTE_SCRIPT'
set -euo pipefail

if which node_exporter >/dev/null 2>&1 || systemctl is-active node_exporter >/dev/null 2>&1; then
    echo "[OK] node_exporter already installed"
    systemctl status node_exporter --no-pager | head -5
    exit 0
fi

NE_VERSION="1.7.0"
NE_URL="https://github.com/prometheus/node_exporter/releases/download/v${NE_VERSION}/node_exporter-${NE_VERSION}.linux-amd64.tar.gz"

cd /tmp
wget -q "$NE_URL" -O node_exporter.tar.gz
tar xzf node_exporter.tar.gz
sudo cp node_exporter-${NE_VERSION}.linux-amd64/node_exporter /usr/local/bin/
sudo chmod +x /usr/local/bin/node_exporter
rm -rf node_exporter.tar.gz node_exporter-${NE_VERSION}.linux-amd64

# Create systemd service
sudo tee /etc/systemd/system/node_exporter.service > /dev/null << 'EOF'
[Unit]
Description=Node Exporter
After=network.target

[Service]
User=nobody
Group=nogroup
ExecStart=/usr/local/bin/node_exporter
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable node_exporter
sudo systemctl start node_exporter

# Open firewall port if ufw active
if sudo ufw status | grep -q "Status: active"; then
    sudo ufw allow 9100/tcp comment "node_exporter"
fi

echo "[OK] node_exporter installed and running on port 9100"
REMOTE_SCRIPT
