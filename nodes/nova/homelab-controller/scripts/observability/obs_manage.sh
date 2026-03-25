#!/usr/bin/env bash
# Observability stack management
set -euo pipefail
export LANG=C.UTF-8 LC_ALL=C.UTF-8

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

case "${1:-status}" in
    up|start)
        echo "Starting observability stack..."
        cd "$SCRIPT_DIR"
        docker compose up -d
        echo "[OK] Stack started"
        echo "  Prometheus: http://$(hostname -I | awk '{print $1}'):9090"
        echo "  Grafana:    http://$(hostname -I | awk '{print $1}'):3000 (admin/homelab)"
        echo "  Loki:       http://$(hostname -I | awk '{print $1}'):3100"
        ;;
    down|stop)
        echo "Stopping observability stack..."
        cd "$SCRIPT_DIR"
        docker compose down
        echo "[OK] Stack stopped"
        ;;
    status)
        echo "Observability Stack Status"
        echo "========================="
        if docker ps --format '{{.Names}}' 2>/dev/null | grep -qE 'prometheus|grafana|loki'; then
            echo "Status: RUNNING"
            docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null | grep -E 'NAMES|prometheus|grafana|loki|promtail|node_exporter'
        else
            echo "Status: STOPPED"
            echo "Run: oc obs up"
        fi
        ;;
    logs)
        cd "$SCRIPT_DIR"
        docker compose logs --tail=50 ${2:-}
        ;;
    export)
        echo "Exporting Grafana dashboards..."
        EXPORT_DIR="$SCRIPT_DIR/grafana/dashboards"
        mkdir -p "$EXPORT_DIR"
        for uid in node-health openclaw-health; do
            curl -s "http://admin:${GF_ADMIN_PASSWORD:-homelab}@localhost:3000/api/dashboards/uid/$uid" 2>/dev/null | \
                python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d.get('dashboard',{}),indent=2))" \
                > "$EXPORT_DIR/${uid}.json" 2>/dev/null || echo "[WARN] Could not export $uid"
        done
        echo "[OK] Dashboards exported to $EXPORT_DIR"
        ;;
    *)
        echo "Usage: obs_manage.sh [up|down|status|logs|export]"
        exit 1
        ;;
esac
