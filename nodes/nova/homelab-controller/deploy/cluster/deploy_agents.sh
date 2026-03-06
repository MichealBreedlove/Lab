#!/usr/bin/env bash
# Deploy OpenClaw agent runtime to cluster nodes.
# Run from the homelab-controller root on Nova.
#
# Usage: bash deploy/cluster/deploy_agents.sh [--start]
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
API_URL="http://10.1.1.21:8081"
DEPLOY_DIR="/opt/openclaw"
START_AFTER=${1:-""}

NODES=("nova" "mira" "orin")
NODE_IPS=("10.1.1.21" "10.1.1.22" "10.1.1.23")

echo "╔══════════════════════════════════════════╗"
echo "║  OpenClaw Agent Deployment               ║"
echo "╚══════════════════════════════════════════╝"
echo ""

for i in "${!NODES[@]}"; do
    NODE="${NODES[$i]}"
    IP="${NODE_IPS[$i]}"
    echo "━━━ Deploying to $NODE ($IP) ━━━"

    # Check connectivity
    if ! ssh -o ConnectTimeout=5 "$NODE@$IP" "echo ok" >/dev/null 2>&1; then
        echo "  [SKIP] Cannot reach $NODE@$IP"
        continue
    fi

    # Create directory structure
    ssh "$NODE@$IP" "sudo mkdir -p $DEPLOY_DIR/{agents,cluster,events,memory,network,proxmox,aiops,config/agents,data/{cluster/agents,tasks,events,artifacts,memory/entries,memory/relations,network_audit,proxmox_audit,reports}} 2>/dev/null; sudo chown -R $NODE:$NODE $DEPLOY_DIR"

    # Deploy agent runtime + base agent
    scp -q "$ROOT/platform/agents/agent_runtime.py" "$NODE@$IP:$DEPLOY_DIR/agents/"
    scp -q "$ROOT/platform/agents/base_agent.py" "$NODE@$IP:$DEPLOY_DIR/agents/"
    scp -q "$ROOT/platform/agents/${NODE}_agent.py" "$NODE@$IP:$DEPLOY_DIR/agents/" 2>/dev/null

    # Deploy cluster modules
    for mod in registry.py task_bus.py router.py health.py execution_policy.py handoff.py scheduler.py; do
        [ -f "$ROOT/platform/cluster/$mod" ] && scp -q "$ROOT/platform/cluster/$mod" "$NODE@$IP:$DEPLOY_DIR/cluster/"
    done

    # Deploy events
    [ -f "$ROOT/platform/events/bus.py" ] && scp -q "$ROOT/platform/events/bus.py" "$NODE@$IP:$DEPLOY_DIR/events/"

    # Deploy memory modules
    for mod in "$ROOT/platform/memory/"*.py; do
        [ -f "$mod" ] && scp -q "$mod" "$NODE@$IP:$DEPLOY_DIR/memory/"
    done

    # Deploy domain modules (network/proxmox/aiops)
    for mod in "$ROOT/platform/network/"*.py; do
        [ -f "$mod" ] && scp -q "$mod" "$NODE@$IP:$DEPLOY_DIR/network/"
    done
    for mod in "$ROOT/platform/proxmox/"*.py; do
        [ -f "$mod" ] && scp -q "$mod" "$NODE@$IP:$DEPLOY_DIR/proxmox/"
    done
    for mod in "$ROOT/platform/aiops/"*.py; do
        [ -f "$mod" ] && scp -q "$mod" "$NODE@$IP:$DEPLOY_DIR/aiops/"
    done

    # Deploy config
    scp -q "$ROOT/config/agents/${NODE}.json" "$NODE@$IP:$DEPLOY_DIR/config/agents/"
    for cfg in "$ROOT/config/"*.json; do
        [ -f "$cfg" ] && scp -q "$cfg" "$NODE@$IP:$DEPLOY_DIR/config/"
    done

    # Deploy systemd service
    ssh "$NODE@$IP" "cat > /tmp/openclaw-agent.service << 'EOF'
[Unit]
Description=OpenClaw Distributed Agent ($NODE)
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 $DEPLOY_DIR/agents/agent_runtime.py --config $DEPLOY_DIR/config/agents/${NODE}.json --api $API_URL
WorkingDirectory=$DEPLOY_DIR
Restart=always
RestartSec=10
User=$NODE
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF
sudo mv /tmp/openclaw-agent.service /etc/systemd/system/openclaw-agent.service
sudo systemctl daemon-reload
sudo systemctl enable openclaw-agent"

    echo "  [OK] Files deployed"
    echo "  [OK] Service installed and enabled"

    if [ "$START_AFTER" = "--start" ]; then
        ssh "$NODE@$IP" "sudo systemctl start openclaw-agent"
        sleep 2
        STATUS=$(ssh "$NODE@$IP" "systemctl is-active openclaw-agent 2>/dev/null")
        echo "  [OK] Service started: $STATUS"
    else
        echo "  [INFO] Service not started (use --start to auto-start)"
    fi
    echo ""
done

echo "━━━ Deployment Summary ━━━"
for i in "${!NODES[@]}"; do
    NODE="${NODES[$i]}"
    IP="${NODE_IPS[$i]}"
    STATUS=$(ssh -o ConnectTimeout=3 "$NODE@$IP" "systemctl is-active openclaw-agent 2>/dev/null" 2>/dev/null || echo "unreachable")
    echo "  $NODE ($IP): $STATUS"
done
echo ""
echo "Manage: sudo systemctl {start|stop|restart|status} openclaw-agent"
echo "Logs:   sudo journalctl -u openclaw-agent -f"
