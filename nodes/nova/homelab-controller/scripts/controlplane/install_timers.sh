#!/usr/bin/env bash
# Install systemd user timers for homelab control plane on Nova
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/../.."

SYSTEMD_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_DIR"

# Daily quick tick service
cat > "$SYSTEMD_DIR/homelab-tick-quick.service" << EOF
[Unit]
Description=Homelab Quick Inventory Tick

[Service]
Type=oneshot
WorkingDirectory=$ROOT_DIR
ExecStart=$SCRIPT_DIR/homelab_tick.sh quick
StandardOutput=journal
StandardError=journal
EOF

# Daily quick tick timer (6 AM)
cat > "$SYSTEMD_DIR/homelab-tick-quick.timer" << EOF
[Unit]
Description=Daily homelab quick inventory

[Timer]
OnCalendar=*-*-* 06:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Weekly full tick service
cat > "$SYSTEMD_DIR/homelab-tick-full.service" << EOF
[Unit]
Description=Homelab Full Inventory Tick

[Service]
Type=oneshot
WorkingDirectory=$ROOT_DIR
ExecStart=$SCRIPT_DIR/homelab_tick.sh full push
StandardOutput=journal
StandardError=journal
EOF

# Weekly full tick timer (Sunday 3 AM)
cat > "$SYSTEMD_DIR/homelab-tick-full.timer" << EOF
[Unit]
Description=Weekly homelab full inventory

[Timer]
OnCalendar=Sun *-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

# Enable and start timers
systemctl --user daemon-reload
systemctl --user enable homelab-tick-quick.timer
systemctl --user enable homelab-tick-full.timer
systemctl --user start homelab-tick-quick.timer
systemctl --user start homelab-tick-full.timer

echo "✅ Systemd timers installed:"
systemctl --user list-timers homelab-tick-*
