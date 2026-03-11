#!/bin/bash
# Configure systemd journal size limits and log rotation
echo "=== $(hostname): configuring log rotation ==="

# Cap journal to 500MB max
mkdir -p /etc/systemd/journald.conf.d
cat > /etc/systemd/journald.conf.d/size-limit.conf << 'EOF'
[Journal]
SystemMaxUse=500M
SystemKeepFree=2G
MaxRetentionSec=2week
EOF
systemctl restart systemd-journald
echo "Journal capped at 500MB / 2 weeks"

# Add weekly log cleanup cron
cat > /etc/cron.weekly/clean-logs << 'EOF'
#!/bin/bash
journalctl --vacuum-size=400M --vacuum-time=2week
apt-get autoremove -y -qq
apt-get clean -qq
docker system prune -f 2>/dev/null || true
EOF
chmod +x /etc/cron.weekly/clean-logs
echo "Weekly log cleanup cron added"

df -h /
echo "=== Done: $(hostname) ==="
