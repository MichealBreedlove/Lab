#!/usr/bin/env bash
# install_timer.sh — Install a systemd user timer for daily Lab backup
# Run on each Linux node (nova/mira/orin)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
UNIT_DIR="$HOME/.config/systemd/user"

mkdir -p "$UNIT_DIR"

# --- Service unit ---
cat > "$UNIT_DIR/lab-backup.service" <<EOF
[Unit]
Description=Lab GitHub Backup

[Service]
Type=oneshot
ExecStart=/bin/bash $SCRIPT_DIR/lab-backup.sh
WorkingDirectory=$HOME/Lab
EOF

# --- Timer unit (daily at 2:30 AM) ---
cat > "$UNIT_DIR/lab-backup.timer" <<EOF
[Unit]
Description=Lab Backup Daily Timer

[Timer]
OnCalendar=*-*-* 02:30:00
Persistent=true
RandomizedDelaySec=300

[Install]
WantedBy=timers.target
EOF

# --- Lightweight hourly sync ---
cat > "$UNIT_DIR/lab-sync.service" <<EOF
[Unit]
Description=Lab Git Sync

[Service]
Type=oneshot
ExecStart=/bin/bash $SCRIPT_DIR/lab-git-push.sh
WorkingDirectory=$HOME/Lab
EOF

cat > "$UNIT_DIR/lab-sync.timer" <<EOF
[Unit]
Description=Lab Git Sync Hourly

[Timer]
OnCalendar=hourly
Persistent=true
RandomizedDelaySec=120

[Install]
WantedBy=timers.target
EOF

# --- Enable ---
systemctl --user daemon-reload
systemctl --user enable --now lab-backup.timer
systemctl --user enable --now lab-sync.timer

echo "=== Timers installed ==="
systemctl --user list-timers lab-backup.timer lab-sync.timer
echo ""
echo "To test now: systemctl --user start lab-backup.service"
