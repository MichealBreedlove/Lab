#!/usr/bin/env bash
# oc.sh — Homelab controller CLI
# Usage: oc <command> [args...]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$SCRIPT_DIR/.."

show_help() {
    cat <<'EOF'
oc — Homelab Controller CLI

Commands:
  ping                  Test SSH connectivity to all nodes
  health                Collect health reports from all nodes
  oc-status             Check OpenClaw status on all nodes
  snapshot              Run snapshot collection
  slo                   Show current SLO status
  slo eval              Run SLO evaluation
  slo report            Generate SLO reports
  slo burn              Show burn rates
  slo budget            Show error budgets
  slo publish           Publish SLO data to dashboard/telegram
  slo test              Run P27 SLO tests
  incident              Show active incident status
  incident open         Open a new incident
  incident note         Add a note to active incident
  incident close        Close an incident
  incident timeline     Show incident timeline
  incident list         List all incidents
  incident postmortem   Generate postmortem for latest resolved
  incident tick         Run incident trigger check
  incident test         Run P28 incident tests
  changelog             Run changelog generation (P26)
  gate <action> <tier>  Evaluate gatekeeper for an action
  test <priority>       Run tests for a priority (e.g., test p27)
  backup                Run Lab backup for this node
  help                  Show this help

Options:
  --limit <node>        Target specific node (e.g., --limit mira)
  --dry-run             Don't actually execute/publish
EOF
}

cmd_slo() {
    local subcmd="${1:-status}"
    shift 2>/dev/null || true

    case "$subcmd" in
        status|"")
            echo "=== SLO Status ==="
            cd "$ROOT_DIR"
            if [ -f artifacts/slo/current.json ]; then
                python3 -c "
import json
r = json.load(open('artifacts/slo/current.json'))
s = r.get('summary', {})
print(f'Last evaluated: {r.get(\"timestamp\", \"never\")}')
print(f'SLOs: {s.get(\"total_slos\",0)} total')
print(f'  ✅ {s.get(\"slos_meeting_objective\",0)} meeting objective')
print(f'  ⚠️  {s.get(\"slos_at_risk\",0)} at risk')
print(f'  🔴 {s.get(\"slos_exhausted\",0)} budget exhausted')
print(f'  🚨 {s.get(\"active_alerts\",0)} active alerts')
print()
for slo_id, slo in r.get('slos', {}).items():
    b = slo.get('budget', {})
    icon = '🔴' if b.get('budget_exhausted') else '🟡' if b.get('budget_at_risk') else '🟢'
    print(f'  {icon} {slo.get(\"name\", slo_id)}: {b.get(\"remaining_budget_pct\", \"?\")}% budget remaining (SLI: {b.get(\"sli_current\", \"N/A\")})')
"
            else
                echo "No SLO data yet. Run: oc slo eval"
            fi
            ;;
        eval)
            echo "=== Running SLO Evaluation ==="
            cd "$ROOT_DIR"
            python3 scripts/slo_runner.py "$@"
            ;;
        report)
            echo "=== SLO Report ==="
            cd "$ROOT_DIR/scripts/slo"
            python3 -c "
from slo_render import render_markdown_report
from slo_utils import ARTIFACTS_DIR, load_json
f = ARTIFACTS_DIR / 'current.json'
if f.exists():
    print(render_markdown_report(load_json(f)))
else:
    print('No data. Run: oc slo eval')
"
            ;;
        burn)
            echo "=== Burn Rates ==="
            cd "$ROOT_DIR"
            python3 -c "
import json
r = json.load(open('artifacts/slo/current.json'))
for slo_id, slo in r.get('slos', {}).items():
    print(f'\n{slo.get(\"name\", slo_id)}:')
    for wname, w in slo.get('burn_rates', {}).items():
        br = w.get('burn_rate')
        br_str = f'{br:.2f}x' if br is not None else 'N/A'
        flag = ' ⚠️' if br and br > 1 else ''
        print(f'  {wname}: {br_str}{flag}')
" 2>/dev/null || echo "No data. Run: oc slo eval"
            ;;
        budget)
            echo "=== Error Budgets ==="
            cd "$ROOT_DIR"
            python3 -c "
import json
r = json.load(open('artifacts/slo/current.json'))
for slo_id, slo in r.get('slos', {}).items():
    b = slo.get('budget', {})
    icon = '🔴' if b.get('budget_exhausted') else '🟡' if b.get('budget_at_risk') else '🟢'
    print(f'{icon} {slo.get(\"name\", slo_id)}:')
    print(f'    Objective: {slo.get(\"objective\", \"?\")}')
    print(f'    Budget:    {b.get(\"remaining_budget_pct\", \"?\")}% remaining')
    print(f'    Bad events: {b.get(\"bad_events\", 0)} / {b.get(\"allowed_bad_events\", 0)} allowed')
    print()
" 2>/dev/null || echo "No data. Run: oc slo eval"
            ;;
        publish)
            echo "=== Publishing SLO Data ==="
            cd "$ROOT_DIR/scripts/slo"
            python3 -c "
from slo_publish import publish
from slo_utils import ARTIFACTS_DIR, load_json
f = ARTIFACTS_DIR / 'current.json'
if f.exists():
    publish(load_json(f))
else:
    print('No data. Run: oc slo eval')
"
            ;;
        test)
            bash "$ROOT_DIR/scripts/test_priority27_slo.sh"
            ;;
        *)
            echo "Unknown slo subcommand: $subcmd"
            echo "Try: oc slo [status|eval|report|burn|budget|publish|test]"
            exit 1
            ;;
    esac
}

# Main dispatch
case "${1:-help}" in
    ping)
        shift
        ansible-playbook "$ROOT_DIR/playbooks/ping.yml" "$@"
        ;;
    health)
        shift
        bash "$ROOT_DIR/scripts/run_health.sh" "$@"
        ;;
    oc-status)
        shift
        ansible-playbook "$ROOT_DIR/playbooks/openclaw_status.yml" "$@"
        ;;
    slo)
        shift
        cmd_slo "$@"
        ;;
    incident)
        shift
        subcmd="${1:-status}"
        shift 2>/dev/null || true
        case "$subcmd" in
            status)
                cd "$ROOT_DIR/scripts/incident"
                python3 incident_manager.py status
                ;;
            open)
                cd "$ROOT_DIR/scripts/incident"
                python3 incident_manager.py open "$@"
                ;;
            note)
                cd "$ROOT_DIR/scripts/incident"
                python3 incident_manager.py note "$@"
                ;;
            close)
                cd "$ROOT_DIR/scripts/incident"
                python3 incident_manager.py close "$@"
                ;;
            timeline)
                cd "$ROOT_DIR/scripts/incident"
                python3 incident_manager.py timeline "$@"
                ;;
            list)
                cd "$ROOT_DIR/scripts/incident"
                python3 incident_manager.py list "$@"
                ;;
            postmortem)
                cd "$ROOT_DIR/scripts/incident"
                python3 incident_render.py "$@"
                ;;
            tick)
                bash "$ROOT_DIR/scripts/incident/incident_tick.sh"
                ;;
            test)
                bash "$ROOT_DIR/scripts/incident/test_priority28_incidents.sh"
                ;;
            *)
                echo "Unknown incident subcommand: $subcmd"
                echo "Try: oc incident [status|open|note|close|timeline|list|postmortem|tick|test]"
                ;;
        esac
        ;;
    gate)
        shift
        cd "$ROOT_DIR"
        python3 scripts/gatekeeper.py "$@" 2>/dev/null || echo "Gatekeeper not available (P25)"
        ;;
    changelog)
        shift
        cd "$ROOT_DIR"
        python3 scripts/changelog_runner.py "$@" 2>/dev/null || echo "Changelog not available (P26)"
        ;;
    snapshot)
        shift
        cd "$ROOT_DIR"
        bash scripts/run_snapshot.sh "$@" 2>/dev/null || echo "Snapshot runner not available"
        ;;
    test)
        shift
        priority="${1:-all}"
        case "$priority" in
            p27|slo) bash "$ROOT_DIR/scripts/test_priority27_slo.sh" ;;
            p28|incident) bash "$ROOT_DIR/scripts/incident/test_priority28_incidents.sh" ;;
            all)
                echo "Running all available tests..."
                for t in "$ROOT_DIR"/scripts/test_priority*.sh; do
                    [ -f "$t" ] && bash "$t"
                done
                ;;
            *) echo "Unknown test target: $priority" ;;
        esac
        ;;
    backup)
        shift
        bash "$(dirname "$ROOT_DIR")/../../../tools/backup/linux/lab-backup.sh" "$@"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
