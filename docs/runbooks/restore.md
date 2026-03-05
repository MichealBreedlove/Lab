# Restore Runbook

## Full Node Restore

### 1. Reinstall OS
- Nova/Mira/Orin: Ubuntu Server (latest LTS)
- Jasper: Windows 11

### 2. Pull Latest Configs
```bash
git clone https://github.com/MichealBreedlove/Lab.git
cd Lab/nodes/<node>/
```

### 3. Reinstall Core Packages
```bash
# Linux nodes
sudo apt-get update
sudo apt-get install -y ansible openssh-client python3 git curl

# Install Node.js (for OpenClaw)
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo bash -
sudo apt-get install -y nodejs

# Install OpenClaw
npm install -g openclaw
```

### 4. Restore OpenClaw Config
```bash
cp nodes/<node>/openclaw/config/* ~/.openclaw/
openclaw gateway start  # or openclaw node start
```

### 5. Re-pair Nodes (if needed)
On gateway (Jasper):
```
openclaw node pair
```
On each node:
```
openclaw node approve <request-id>
```

### 6. Restore Ansible Controller (Nova only)
```bash
cd ~/
cp -r Lab/nodes/nova/homelab-controller ~/homelab-controller
cd ~/homelab-controller
./bootstrap_controller.sh
```

### 7. Verify
```bash
./scripts/run_ping.sh
./scripts/run_health.sh
```

## Partial Restore (Single Service)
If only OpenClaw is broken:
1. `npm install -g openclaw`
2. Copy config from `nodes/<node>/openclaw/config/`
3. Restart service: `sudo systemctl restart openclaw-node`
