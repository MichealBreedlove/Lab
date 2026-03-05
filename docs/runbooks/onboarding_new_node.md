# Onboarding a New Node

## Prerequisites
- Ubuntu Server installed
- Network connected on 10.1.1.x subnet
- SSH access from Nova

## Steps

### 1. Set hostname
```bash
sudo hostnamectl set-hostname <nodename>
```

### 2. Install SSH key from Nova
On Nova:
```bash
ssh-copy-id -i ~/.ssh/id_ed25519_homelab.pub <user>@<node-ip>
```

### 3. Add to Ansible inventory
Edit `~/homelab-controller/inventory.ini`:
```ini
[remote_nodes]
<nodename> ansible_host=10.1.1.XX ansible_user=<user>
```

### 4. Verify connectivity
```bash
./scripts/run_ping.sh --limit <nodename>
```

### 5. Install OpenClaw
```bash
# On the new node
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo bash -
sudo apt-get install -y nodejs
npm install -g openclaw
```

### 6. Create systemd service
```bash
sudo tee /etc/systemd/system/openclaw-node.service > /dev/null <<'EOF'
[Unit]
Description=OpenClaw Node
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/local/bin/openclaw node start
Restart=on-failure
RestartSec=10
User=<user>
Environment=HOME=/home/<user>

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now openclaw-node
```

### 7. Pair with gateway
On Jasper: `openclaw node pair`
On new node: `openclaw node approve <id>`

### 8. Add to Lab repo
```bash
mkdir -p ~/Lab/nodes/<nodename>/{openclaw,system,logs}
```

### 9. Set up backup timer
```bash
cd ~/Lab
bash tools/backup/linux/install_timer.sh
```
