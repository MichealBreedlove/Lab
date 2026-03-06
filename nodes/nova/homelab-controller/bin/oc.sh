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
  portfolio             Show portfolio publish status
  portfolio build       Build site content
  portfolio publish     Publish to GitHub Pages
  portfolio tick        Full pipeline (redact → build → publish)
  portfolio test        Run P29 portfolio tests
  changelog             Run changelog generation (P26)
  gate <action> <tier>  Evaluate gatekeeper for an action
  auth token create      Create access token
  auth token revoke      Revoke a token
  auth token list        List active tokens
  auth audit             Show audit summary
  auth whoami            Show current identity
  auth test              Run auth self-test
  platform status        Platform API status
  platform chaos         Trigger chaos via API
  platform change        Trigger change via API
  platform snapshot      Trigger snapshot via API
  change list            List recent changes
  change show <id>       Show a specific change
  change create <trigger> <summary>  Create new change
  change validate <id>   Validate a change
  drift status           Show drift detection status
  drift run              Run full drift detection pipeline
  obs up|down|status     Manage observability stack
  obs export             Export Grafana dashboards
  demo run <scenario>    Run reliability demo scenario
  demo list              List available demo scenarios
  controlplane tick      Quick inventory tick (nodes + BIOS)
  controlplane full      Full inventory tick (all devices)
  controlplane status    Show last tick results
  controlplane connectivity  Scan all device ports
  controlplane test      Run P43 control plane tests
  supply status          Supply chain health overview
  supply sbom            Generate SBOM
  supply provenance      Record build provenance
  supply harden          Run hardening checks
  supply tick            Full supply chain pipeline
  supply test            Run P41 supply chain tests
  verify status          Verification health overview
  verify synthetic       Run synthetic endpoint probes
  verify canary          Run canary function probes
  verify gates           Evaluate policy gates
  verify tick            Full verification pipeline
  verify test            Run P40 verification tests
  portfolio render       Generate recruiter portfolio docs
  portfolio status       Portfolio export status
  portfolio tick         Full portfolio pipeline
  portfolio test         Run P39 portfolio tests
  sec status             Security status overview
  sec audit              Run baseline audit on all nodes
  sec scan               Run secret scanner
  sec tick               Full security pipeline
  sec test               Run P38 security tests
  infra status           Infrastructure health status
  infra inventory        Collect node inventory
  infra backup           Export Proxmox + check OPNsense
  infra tick             Full infrastructure pipeline
  infra test             Run P37 infra tests
  obs status             Observability stack status
  obs install            Install Docker + stack directories [--apply]
  obs up                 Start observability stack
  obs down               Stop observability stack
  obs logs               View stack logs
  obs tick               Run observability tick
  obs event              Event bus (write|read|types)
  obs test               Run P36 observability tests
  release audit          Run release audit (configs, scripts, secrets)
  release docs           Generate release documentation
  release package        Build release manifest
  release tag            Create v1.0.0 git tag [--apply]
  release test           Run P35 release tests
  aiops anomaly          Detect anomalies in capacity metrics
  aiops correlate        Correlate alerts into incidents
  aiops analyze          AI-powered cluster analysis
  aiops report           Generate operations report
  aiops tick             Run full AIOps pipeline
  aiops test             Run P34 AIOps tests
  docs generate          Generate all documentation
  docs topology          Generate topology docs
  docs services          Generate services catalog
  docs deps              Generate dependency map
  docs changelog         Generate changelog from git
  docs test              Run P33 docs tests
  capacity collect       Collect capacity metrics from all nodes
  capacity forecast      Forecast resource exhaustion
  capacity recommend     Generate capacity recommendations
  capacity tick          Run full capacity pipeline
  capacity test          Run P32 capacity tests
  bootstrap node <name> Bootstrap a node [--apply]
  bootstrap status      Show bootstrap status for all nodes
  bootstrap validate    Validate bootstrapped node [--node <name>]
  bootstrap test        Run P31 bootstrap tests
  dr status             Show DR readiness status
  dr preflight          Run DR preflight checks
  dr restore [opts]     Run restore (--dry-run|--apply) [--node <name>]
  dr validate           Validate node restore state [--node <name>]
  dr drill              Run DR drill [--node <name>] [--max-actions N]
  dr tick               Run DR tick (timer wrapper)
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
    portfolio)
        shift
        subcmd="${1:-status}"
        shift 2>/dev/null || true
        case "$subcmd" in
            status)
                LATEST="$ROOT_DIR/../../services/openclaw/portfolio/latest.json"
                if [ -f "$LATEST" ]; then
                    python3 -c "
import json
d = json.load(open('$LATEST'))
print(f'Last publish: {d.get(\"last_publish\", \"never\")}')
print(f'Success: {d.get(\"success\", \"?\")}')
print(f'Site: {d.get(\"site_url\", \"N/A\")}')
"
                else
                    echo "No portfolio published yet. Run: oc portfolio tick"
                fi
                ;;
            build)
                cd "$ROOT_DIR/scripts/portfolio"
                python3 portfolio_build.py
                ;;
            publish)
                cd "$ROOT_DIR/scripts/portfolio"
                python3 portfolio_publish.py
                ;;
            tick)
                bash "$ROOT_DIR/scripts/portfolio/portfolio_tick.sh"
                ;;
            test)
                bash "$ROOT_DIR/scripts/portfolio/test_priority29_portfolio.sh"
                ;;
            open)
                URL=$(python3 -c "import json; print(json.load(open('$ROOT_DIR/config/portfolio_policy.json')).get('publish_target',{}).get('site_url',''))" 2>/dev/null)
                if [ -n "$URL" ]; then
                    echo "Opening: $URL"
                    xdg-open "$URL" 2>/dev/null || open "$URL" 2>/dev/null || echo "Open manually: $URL"
                else
                    echo "No site URL configured."
                fi
                ;;
            render)
                cd "$ROOT_DIR"; python3 scripts/portfolio/portfolio_render.py "$@"
                ;;
            badges)
                cd "$ROOT_DIR"; python3 scripts/portfolio/portfolio_badges.py "$@"
                ;;
            *)
                echo "Unknown portfolio subcommand: $subcmd"
                echo "Try: oc portfolio [status|build|publish|render|badges|tick|test|open]"
                ;;
        esac
        ;;
    recovery)
        shift
        subcmd="${1:-status}"
        shift 2>/dev/null || true
        python3 "$ROOT_DIR/platform/recovery/engine.py" "$subcmd" "$@"
        ;;
    auth)
        shift
        subcmd="${1:-whoami}"
        shift 2>/dev/null || true
        case "$subcmd" in
            token)
                action="${1:-list}"
                shift 2>/dev/null || true
                case "$action" in
                    create) python3 "$ROOT_DIR/scripts/identity/token_issuer.py" create "$@" ;;
                    revoke) python3 "$ROOT_DIR/scripts/identity/token_issuer.py" revoke "$@" ;;
                    list) python3 "$ROOT_DIR/scripts/identity/token_issuer.py" list "$@" ;;
                    *) echo "Usage: oc auth token [create|revoke|list]" ;;
                esac
                ;;
            service-account|sa)
                shift 2>/dev/null || true
                sa_cmd="${1:-list}"
                shift 2>/dev/null || true
                python3 "$ROOT_DIR/scripts/identity/service_accounts.py" "$sa_cmd" "$@"
                ;;
            audit) python3 "$ROOT_DIR/scripts/identity/audit_log.py" summary ;;
            whoami) python3 "$ROOT_DIR/scripts/identity/auth_manager.py" whoami "$@" ;;
            test) python3 "$ROOT_DIR/scripts/identity/auth_manager.py" test ;;
            tick) bash "$ROOT_DIR/scripts/identity/identity_tick.sh" ;;
            *) echo "Usage: oc auth [token create|token revoke|token list|audit|whoami|test|tick]" ;;
        esac
        ;;
    platform)
        shift
        subcmd="${1:-status}"
        shift 2>/dev/null || true
        API_URL="http://localhost:8081"
        case "$subcmd" in
            status)
                echo "Platform API Status"
                if curl -sf "$API_URL/" >/dev/null 2>&1; then
                    curl -sf "$API_URL/" | python3 -m json.tool
                else
                    echo "  API not running. Start with: oc platform start"
                fi
                ;;
            start)
                bash "$ROOT_DIR/platform/install_platform_api.sh"
                ;;
            stop)
                systemctl --user stop homelab-platform-api.service 2>/dev/null || true
                echo "[OK] Platform API stopped"
                ;;
            chaos)
                scenario="${1:-gateway_restart_outage}"
                curl -sf -X POST "$API_URL/chaos" -H 'Content-Type: application/json' \
                    -d "{\"scenario\":\"$scenario\"}" | python3 -m json.tool
                ;;
            change)
                trigger="${1:-manual}"
                shift 2>/dev/null || true
                summary="${*:-API change}"
                curl -sf -X POST "$API_URL/change" -H 'Content-Type: application/json' \
                    -d "{\"trigger\":\"$trigger\",\"summary\":\"$summary\"}" | python3 -m json.tool
                ;;
            snapshot)
                curl -sf -X POST "$API_URL/snapshot" -H 'Content-Type: application/json' \
                    -d '{}' | python3 -m json.tool
                ;;
            *) echo "Usage: oc platform [status|start|stop|chaos|change|snapshot]" ;;
        esac
        ;;
    change)
        shift
        subcmd="${1:-list}"
        shift 2>/dev/null || true
        case "$subcmd" in
            list)
                echo "Recent Changes:"
                if [ -d "$ROOT_DIR/changes" ]; then
                    ls -1d "$ROOT_DIR/changes"/CHG-* 2>/dev/null | sort -r | head -20 | while read d; do
                        id=$(basename "$d")
                        if [ -f "$d/change.json" ]; then
                            trigger=$(python3 -c "import json; print(json.load(open('$d/change.json')).get('trigger','?'))" 2>/dev/null)
                            status=$(python3 -c "import json; print(json.load(open('$d/change.json')).get('status','?'))" 2>/dev/null)
                            echo "  $id  [$trigger]  $status"
                        else
                            echo "  $id  (no metadata)"
                        fi
                    done
                else
                    echo "  No changes recorded yet."
                fi
                ;;
            show)
                cid="${1:?Usage: oc change show <change_id>}"
                if [ -f "$ROOT_DIR/changes/$cid/change.md" ]; then
                    cat "$ROOT_DIR/changes/$cid/change.md"
                elif [ -f "$ROOT_DIR/changes/$cid/change.json" ]; then
                    python3 -m json.tool "$ROOT_DIR/changes/$cid/change.json"
                else
                    echo "Change not found: $cid"
                fi
                ;;
            create)
                trigger="${1:-manual}"
                shift 2>/dev/null || true
                summary="$*"
                python3 "$ROOT_DIR/scripts/change/change_create.py" "$trigger" "$summary"
                ;;
            validate)
                cid="${1:-}"
                python3 "$ROOT_DIR/scripts/change/change_validate.py" "$cid"
                ;;
            *) echo "Usage: oc change [list|show <id>|create <trigger> <summary>|validate <id>]" ;;
        esac
        ;;
    drift)
        shift
        subcmd="${1:-status}"
        shift 2>/dev/null || true
        case "$subcmd" in
            run)
                python3 "$ROOT_DIR/scripts/drift/state_render_desired.py"
                python3 "$ROOT_DIR/scripts/drift/state_collect_observed.py"
                python3 "$ROOT_DIR/scripts/drift/state_drift.py"
                ;;
            status)
                if [ -f "$ROOT_DIR/state/drift/drift_report.json" ]; then
                    python3 -c "import json; d=json.load(open('$ROOT_DIR/state/drift/drift_report.json')); print(f'Drift: {d[\"status\"]} ({d[\"total_drifts\"]} drift(s)) @ {d[\"timestamp\"]}')"
                else
                    echo "No drift report yet. Run: oc drift run"
                fi
                ;;
            *) echo "Usage: oc drift [run|status]" ;;
        esac
        ;;
    obs|observability)
        shift
        subcmd="${1:-status}"
        shift 2>/dev/null || true
        bash "$ROOT_DIR/scripts/observability/obs_manage.sh" "$subcmd" "$@"
        ;;
    demo)
        shift
        subcmd="${1:-list}"
        shift 2>/dev/null || true
        case "$subcmd" in
            run) bash "$ROOT_DIR/scripts/demo/demo_runner.sh" "${1:-gateway_restart_outage}" ;;
            list) echo "Available scenarios: gateway_restart_outage, ollama_unreachable" ;;
            *) echo "Usage: oc demo [run <scenario>|list]" ;;
        esac
        ;;
    controlplane|cp)
        shift
        subcmd="${1:-status}"
        shift 2>/dev/null || true
        case "$subcmd" in
            tick) bash "$ROOT_DIR/scripts/controlplane/homelab_tick.sh" quick ;;
            full) bash "$ROOT_DIR/scripts/controlplane/homelab_tick.sh" full push ;;
            status)
                echo "Control Plane Status"
                ls -lt "$ROOT_DIR/artifacts/controlplane/" 2>/dev/null | head -10 || echo "No artifacts yet. Run: oc controlplane tick"
                ;;
            connectivity) cd "$ROOT_DIR"; python3 scripts/controlplane/device_connectivity.py "$@" ;;
            test) bash "$ROOT_DIR/scripts/controlplane/test_controlplane.sh" ;;
            *) echo "Unknown controlplane subcommand: $subcmd"; echo "Try: oc controlplane [tick|full|status|connectivity|test]" ;;
        esac
        ;;
    supply)
        shift
        subcmd="${1:-status}"
        shift 2>/dev/null || true
        case "$subcmd" in
            status) cd "$ROOT_DIR"; python3 scripts/supply/supply_publish.py ;;
            sbom) cd "$ROOT_DIR"; python3 scripts/supply/supply_sbom.py "$@" ;;
            provenance) cd "$ROOT_DIR"; python3 scripts/supply/supply_provenance.py "$@" ;;
            harden) cd "$ROOT_DIR"; python3 scripts/supply/supply_harden.py "$@" ;;
            tick) bash "$ROOT_DIR/scripts/supply/supply_tick.sh" ;;
            test) bash "$ROOT_DIR/scripts/supply/test_priority41_supply.sh" ;;
            *) echo "Unknown supply subcommand: $subcmd"; echo "Try: oc supply [status|sbom|provenance|harden|tick|test]" ;;
        esac
        ;;
    verify)
        shift
        subcmd="${1:-status}"
        shift 2>/dev/null || true
        case "$subcmd" in
            status) cd "$ROOT_DIR"; python3 scripts/verify/verify_publish.py ;;
            synthetic) cd "$ROOT_DIR"; python3 scripts/verify/verify_synthetic.py "$@" ;;
            canary) cd "$ROOT_DIR"; python3 scripts/verify/verify_canary.py "$@" ;;
            gates) cd "$ROOT_DIR"; python3 scripts/verify/verify_gates.py "$@" ;;
            tick) bash "$ROOT_DIR/scripts/verify/verify_tick.sh" ;;
            test) bash "$ROOT_DIR/scripts/verify/test_priority40_verify.sh" ;;
            *) echo "Unknown verify subcommand: $subcmd"; echo "Try: oc verify [status|synthetic|canary|gates|tick|test]" ;;
        esac
        ;;
    sec)
        shift
        subcmd="${1:-status}"
        shift 2>/dev/null || true
        case "$subcmd" in
            status) cd "$ROOT_DIR"; python3 scripts/sec/sec_publish.py ;;
            audit) cd "$ROOT_DIR"; python3 scripts/sec/sec_baseline_audit.py "$@" ;;
            scan) cd "$ROOT_DIR"; python3 scripts/sec/sec_secretscan.py "$@" ;;
            tick) bash "$ROOT_DIR/scripts/sec/sec_tick.sh" ;;
            test) bash "$ROOT_DIR/scripts/sec/test_priority38_sec.sh" ;;
            *) echo "Unknown sec subcommand: $subcmd"; echo "Try: oc sec [status|audit|scan|tick|test]" ;;
        esac
        ;;
    infra)
        shift
        subcmd="${1:-status}"
        shift 2>/dev/null || true
        case "$subcmd" in
            status) cd "$ROOT_DIR"; python3 scripts/infra/infra_publish.py ;;
            inventory) cd "$ROOT_DIR"; python3 scripts/infra/infra_inventory.py "$@" ;;
            backup) cd "$ROOT_DIR"; python3 scripts/infra/proxmox_export.py "$@"; python3 scripts/infra/opnsense_backup.py "$@" ;;
            tick) bash "$ROOT_DIR/scripts/infra/infra_tick.sh" ;;
            test) bash "$ROOT_DIR/scripts/infra/test_priority37_infra.sh" ;;
            *) echo "Unknown infra subcommand: $subcmd"; echo "Try: oc infra [status|inventory|backup|tick|test]" ;;
        esac
        ;;
    obs)
        shift
        subcmd="${1:-status}"
        shift 2>/dev/null || true
        OBS_DIR="${HOME}/obs-stack"
        case "$subcmd" in
            status) cd "$ROOT_DIR"; python3 scripts/obs/obs_publish.py ;;
            install) bash "$ROOT_DIR/scripts/obs/obs_install.sh" "$@" ;;
            up) cd "$OBS_DIR" 2>/dev/null && docker compose up -d || echo "Stack not installed. Run: oc obs install --apply" ;;
            down) cd "$OBS_DIR" 2>/dev/null && docker compose down || echo "Stack not running" ;;
            logs) cd "$OBS_DIR" 2>/dev/null && docker compose logs --tail=50 || echo "Stack not running" ;;
            tick) bash "$ROOT_DIR/scripts/obs/obs_tick.sh" ;;
            event) cd "$ROOT_DIR"; python3 scripts/obs/obs_eventbus.py "$@" ;;
            test) bash "$ROOT_DIR/scripts/obs/test_priority36_obs.sh" ;;
            *) echo "Unknown obs subcommand: $subcmd"; echo "Try: oc obs [status|install|up|down|logs|tick|event|test]" ;;
        esac
        ;;
    release)
        shift
        subcmd="${1:-audit}"
        shift 2>/dev/null || true
        case "$subcmd" in
            audit) cd "$ROOT_DIR"; python3 scripts/release/release_audit.py "$@" ;;
            docs) cd "$ROOT_DIR"; python3 scripts/release/release_build_docs.py "$@" ;;
            package) cd "$ROOT_DIR"; python3 scripts/release/release_package.py "$@" ;;
            tag) bash "$ROOT_DIR/scripts/release/release_tag.sh" "$@" ;;
            test) bash "$ROOT_DIR/scripts/release/test_priority35_release.sh" ;;
            *) echo "Unknown release subcommand: $subcmd"; echo "Try: oc release [audit|docs|package|tag|test]" ;;
        esac
        ;;
    aiops)
        shift
        subcmd="${1:-tick}"
        shift 2>/dev/null || true
        case "$subcmd" in
            anomaly) cd "$ROOT_DIR"; python3 scripts/aiops/aiops_anomaly.py "$@" ;;
            correlate) cd "$ROOT_DIR"; python3 scripts/aiops/aiops_correlate.py "$@" ;;
            analyze) cd "$ROOT_DIR"; python3 scripts/aiops/aiops_analyze.py "$@" ;;
            report) cd "$ROOT_DIR"; python3 scripts/aiops/aiops_report.py "$@" ;;
            tick) bash "$ROOT_DIR/scripts/aiops/aiops_tick.sh" ;;
            test) bash "$ROOT_DIR/scripts/aiops/test_priority34_aiops.sh" ;;
            *) echo "Unknown aiops subcommand: $subcmd"; echo "Try: oc aiops [anomaly|correlate|analyze|report|tick|test]" ;;
        esac
        ;;
    docs)
        shift
        subcmd="${1:-generate}"
        shift 2>/dev/null || true
        case "$subcmd" in
            generate|all) python3 "$ROOT_DIR/scripts/docs/docs_generate_all.py" ;;
            topology) python3 "$ROOT_DIR/scripts/docs/docs_topology.py" "$@" ;;
            services) python3 "$ROOT_DIR/scripts/docs/docs_services.py" "$@" ;;
            deps|dependencies) python3 "$ROOT_DIR/scripts/docs/docs_dependencies.py" "$@" ;;
            changelog) python3 "$ROOT_DIR/scripts/docs/docs_changelog.py" "$@" ;;
            diagrams) python3 "$ROOT_DIR/scripts/docs/docs_diagrams.py" "$@" ;;
            portfolio) python3 "$ROOT_DIR/scripts/docs/docs_portfolio.py" "$@" ;;
            test) bash "$ROOT_DIR/scripts/docs/test_priority33_docs.sh" ;;
            *) echo "Unknown docs subcommand: $subcmd"; echo "Try: oc docs [generate|topology|services|deps|changelog|test]" ;;
        esac
        ;;
    capacity)
        shift
        subcmd="${1:-tick}"
        shift 2>/dev/null || true
        case "$subcmd" in
            collect)
                cd "$ROOT_DIR"
                python3 scripts/capacity/capacity_collect.py "$@"
                ;;
            forecast)
                cd "$ROOT_DIR"
                python3 scripts/capacity/capacity_forecast.py "$@"
                ;;
            recommend)
                cd "$ROOT_DIR"
                python3 scripts/capacity/capacity_recommend.py "$@"
                ;;
            tick)
                bash "$ROOT_DIR/scripts/capacity/capacity_tick.sh"
                ;;
            test)
                bash "$ROOT_DIR/scripts/capacity/test_priority32_capacity.sh"
                ;;
            *)
                echo "Unknown capacity subcommand: $subcmd"
                echo "Try: oc capacity [collect|forecast|recommend|tick|test]"
                ;;
        esac
        ;;
    bootstrap)
        shift
        subcmd="${1:-status}"
        shift 2>/dev/null || true
        case "$subcmd" in
            node)
                node_name="${1:?Usage: oc bootstrap node <name> [--apply]}"
                shift 2>/dev/null || true
                apply_flag=""
                if [ "${1:-}" = "--apply" ]; then
                    apply_flag="--apply"
                fi
                bash "$ROOT_DIR/scripts/bootstrap/bootstrap_tick.sh" "$node_name" $apply_flag
                ;;
            status)
                echo "=== Bootstrap Status ==="
                cd "$ROOT_DIR"
                for node in nova mira orin jasper; do
                    if [ -f "artifacts/bootstrap/validate_${node}.json" ]; then
                        python3 -c "
import json
d = json.load(open('artifacts/bootstrap/validate_${node}.json'))
s = d.get('summary', {})
icon = '✅' if d.get('pass') else '❌'
print(f'  {icon} ${node}: {s.get(\"passing\",0)}/{s.get(\"total\",0)} checks')
" 2>/dev/null
                    else
                        echo "  ⏭️  ${node}: no data"
                    fi
                done
                ;;
            validate)
                cd "$ROOT_DIR"
                python3 scripts/bootstrap/bootstrap_validate.py "$@"
                ;;
            test)
                bash "$ROOT_DIR/scripts/bootstrap/test_priority31_bootstrap.sh"
                ;;
            *)
                echo "Unknown bootstrap subcommand: $subcmd"
                echo "Try: oc bootstrap [node|status|validate|test]"
                ;;
        esac
        ;;
    dr)
        shift
        subcmd="${1:-status}"
        shift 2>/dev/null || true
        case "$subcmd" in
            status)
                echo "=== DR Status ==="
                cd "$ROOT_DIR"
                if [ -f artifacts/dr/preflight.json ]; then
                    python3 -c "
import json
p = json.load(open('artifacts/dr/preflight.json'))
print(f'Preflight: {\"PASS ✅\" if p.get(\"preflight_pass\") else \"FAIL ❌\"}')
print(f'Node: {p.get(\"node\",\"?\")} ({p.get(\"platform\",\"?\")})')
print(f'Last check: {p.get(\"timestamp\",\"never\")}')
" 2>/dev/null || echo "No preflight data"
                fi
                # Show latest drill
                LATEST_DRILL=$(ls -t artifacts/dr/drill_report_*.json 2>/dev/null | head -1)
                if [ -n "$LATEST_DRILL" ]; then
                    python3 -c "
import json
d = json.load(open('$LATEST_DRILL'))
mttr = d.get('mttr_seconds', '?')
passed = d.get('overall_pass', False)
print(f'Last drill: {d.get(\"timestamp\",\"never\")}')
print(f'  MTTR: {mttr}s')
print(f'  Result: {\"PASS ✅\" if passed else \"FAIL ❌\"}')
" 2>/dev/null || echo "No drill data"
                else
                    echo "No drill reports yet. Run: oc dr drill --node <name>"
                fi
                ;;
            preflight)
                cd "$ROOT_DIR"
                python3 scripts/dr/dr_preflight.py "$@"
                ;;
            restore)
                cd "$ROOT_DIR"
                python3 scripts/dr/dr_restore.py "$@"
                ;;
            validate)
                cd "$ROOT_DIR"
                python3 scripts/dr/dr_validate.py "$@"
                ;;
            drill)
                cd "$ROOT_DIR"
                python3 scripts/dr/dr_drill.py "$@"
                ;;
            tick)
                bash "$ROOT_DIR/scripts/dr/dr_tick.sh" "$@"
                ;;
            test)
                bash "$ROOT_DIR/scripts/dr/test_priority30_dr.sh"
                ;;
            *)
                echo "Unknown dr subcommand: $subcmd"
                echo "Try: oc dr [status|preflight|restore|validate|drill|tick|test]"
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
    memory)
        shift
        subcmd="${1:-status}"
        shift 2>/dev/null || true
        case "$subcmd" in
            status) cd "$ROOT_DIR"; python3 platform/memory/store.py stats ;;
            list) cd "$ROOT_DIR"; python3 platform/memory/store.py list "$@" ;;
            get) cd "$ROOT_DIR"; python3 platform/memory/store.py get "$@" ;;
            search) cd "$ROOT_DIR"; python3 platform/memory/index.py search "$@" ;;
            similar) cd "$ROOT_DIR"; python3 platform/memory/index.py similar "$@" ;;
            graph) cd "$ROOT_DIR"; python3 platform/memory/graph.py "$@" ;;
            relations) cd "$ROOT_DIR"; python3 platform/memory/graph.py stats ;;
            routing) cd "$ROOT_DIR"; python3 platform/memory/routing_history.py "$@" ;;
            hygiene) cd "$ROOT_DIR"; python3 platform/memory/lifecycle.py report ;;
            archive) cd "$ROOT_DIR"; python3 platform/memory/lifecycle.py archive "$@" ;;
            tick) cd "$ROOT_DIR"; python3 platform/memory/lifecycle.py tick "$@"; python3 platform/memory/memory_publish.py ;;
            publish) cd "$ROOT_DIR"; python3 platform/memory/memory_publish.py ;;
            test)
                bash "$ROOT_DIR/platform/tests/test_priority72_memory_store.sh"
                bash "$ROOT_DIR/platform/tests/test_priority73_memory_search.sh"
                bash "$ROOT_DIR/platform/tests/test_priority74_knowledge_graph.sh"
                bash "$ROOT_DIR/platform/tests/test_priority75_memory_aware_investigation.sh"
                bash "$ROOT_DIR/platform/tests/test_priority76_memory_aware_routing.sh"
                bash "$ROOT_DIR/platform/tests/test_priority77_memory_aware_optimization.sh"
                bash "$ROOT_DIR/platform/tests/test_priority78_memory_policy.sh"
                ;;
            *) echo "Unknown memory subcommand: $subcmd"; echo "Try: oc memory [status|list|get|search|similar|graph|relations|routing|hygiene|archive|tick|publish|test]" ;;
        esac
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
            p29|portfolio) bash "$ROOT_DIR/scripts/portfolio/test_priority29_portfolio.sh" ;;
            p30|dr) bash "$ROOT_DIR/scripts/dr/test_priority30_dr.sh" ;;
            p31|bootstrap) bash "$ROOT_DIR/scripts/bootstrap/test_priority31_bootstrap.sh" ;;
            p32|capacity) bash "$ROOT_DIR/scripts/capacity/test_priority32_capacity.sh" ;;
            p33|docs) bash "$ROOT_DIR/scripts/docs/test_priority33_docs.sh" ;;
            p34|aiops) bash "$ROOT_DIR/scripts/aiops/test_priority34_aiops.sh" ;;
            p35|release) bash "$ROOT_DIR/scripts/release/test_priority35_release.sh" ;;
            p36|obs) bash "$ROOT_DIR/scripts/obs/test_priority36_obs.sh" ;;
            p37|infra) bash "$ROOT_DIR/scripts/infra/test_priority37_infra.sh" ;;
            p38|sec) bash "$ROOT_DIR/scripts/sec/test_priority38_sec.sh" ;;
            p39|portfolio) bash "$ROOT_DIR/scripts/portfolio/test_priority39_portfolio.sh" ;;
            p40|verify) bash "$ROOT_DIR/scripts/verify/test_priority40_verify.sh" ;;
            p41|supply) bash "$ROOT_DIR/scripts/supply/test_priority41_supply.sh" ;;
            p42|freeze) bash "$ROOT_DIR/scripts/release/test_priority42_freeze.sh" ;;
            p43|controlplane|cp) bash "$ROOT_DIR/scripts/controlplane/test_controlplane.sh" ;;
            p44|platform) bash "$ROOT_DIR/scripts/demo/test_platform_upgrades.sh" ;;
            p45|change) bash "$ROOT_DIR/scripts/change/test_change_system.sh" ;;
            p46|platform) bash "$ROOT_DIR/platform/tests/test_platform_api.sh" ;;
            p47|identity) bash "$ROOT_DIR/scripts/identity/test_priority47_identity.sh" ;;
            p48|apiauth) bash "$ROOT_DIR/platform/tests/test_priority48_api_auth.sh" ;;
            p49|ratelimit) bash "$ROOT_DIR/platform/tests/test_priority49_rate_limit.sh" ;;
            p50|revocation) bash "$ROOT_DIR/platform/tests/test_priority50_token_revocation.sh" ;;
            p51|serviceaccount) bash "$ROOT_DIR/platform/tests/test_priority51_service_accounts.sh" ;;
            p52|tls) bash "$ROOT_DIR/platform/tests/test_priority52_tls_config.sh" ;;
            p53|selfhealing) bash "$ROOT_DIR/platform/tests/test_priority53_self_healing.sh" ;;
            p54|eventbus) bash "$ROOT_DIR/platform/tests/test_priority54_event_bus.sh" ;;
            p55|investigation) bash "$ROOT_DIR/platform/tests/test_priority55_ai_investigation.sh" ;;
            p56|remediation) bash "$ROOT_DIR/platform/tests/test_priority56_git_remediation.sh" ;;
            p57|policy) bash "$ROOT_DIR/platform/tests/test_priority57_execution_policy.sh" ;;
            p58|alertmanager) bash "$ROOT_DIR/platform/tests/test_priority58_alert_ingestion.sh" ;;
            p59|review) bash "$ROOT_DIR/platform/tests/test_priority59_after_action_review.sh" ;;
            p60|proposal) bash "$ROOT_DIR/platform/tests/test_priority60_improvement_proposal.sh" ;;
            p61|validation) bash "$ROOT_DIR/platform/tests/test_priority61_validation_runner.sh" ;;
            p62|promotionpolicy) bash "$ROOT_DIR/platform/tests/test_priority62_promotion_policy.sh" ;;
            p63|autopromotion) bash "$ROOT_DIR/platform/tests/test_priority63_safe_auto_promotion.sh" ;;
            firewall) bash "$ROOT_DIR/platform/tests/test_firewall_optimizer.sh" ;;
            wifi) bash "$ROOT_DIR/platform/tests/test_wifi_optimizer.sh" ;;
            proxmox) bash "$ROOT_DIR/platform/tests/test_proxmox_optimizer.sh" ;;
            p64|registry) bash "$ROOT_DIR/platform/tests/test_priority64_agent_registry.sh" ;;
            p65|taskbus) bash "$ROOT_DIR/platform/tests/test_priority65_task_bus.sh" ;;
            p66|router) bash "$ROOT_DIR/platform/tests/test_priority66_capability_router.sh" ;;
            p67|agents) bash "$ROOT_DIR/platform/tests/test_priority67_node_agents.sh" ;;
            p68|healthfailover) bash "$ROOT_DIR/platform/tests/test_priority68_agent_health_failover.sh" ;;
            p69|execpolicy) bash "$ROOT_DIR/platform/tests/test_priority69_distributed_execution_policy.sh" ;;
            p70|handoff) bash "$ROOT_DIR/platform/tests/test_priority70_artifact_handoff.sh" ;;
            p71|opsloop) bash "$ROOT_DIR/platform/tests/test_priority71_autonomous_ops_loop.sh" ;;
            p72|memorystore) bash "$ROOT_DIR/platform/tests/test_priority72_memory_store.sh" ;;
            p73|memorysearch) bash "$ROOT_DIR/platform/tests/test_priority73_memory_search.sh" ;;
            p74|knowledgegraph) bash "$ROOT_DIR/platform/tests/test_priority74_knowledge_graph.sh" ;;
            p75|memoryinvestigation) bash "$ROOT_DIR/platform/tests/test_priority75_memory_aware_investigation.sh" ;;
            p76|memoryrouting) bash "$ROOT_DIR/platform/tests/test_priority76_memory_aware_routing.sh" ;;
            p77|memoryoptimization) bash "$ROOT_DIR/platform/tests/test_priority77_memory_aware_optimization.sh" ;;
            p78|memorypolicy) bash "$ROOT_DIR/platform/tests/test_priority78_memory_policy.sh" ;;
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
