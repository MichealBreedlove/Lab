# oc.ps1 — Homelab Controller CLI (Windows/Jasper)
# Usage: .\oc.ps1 <command> [args...]
param(
    [Parameter(Position=0)]
    [string]$Command = "help",

    [Parameter(Position=1, ValueFromRemainingArguments=$true)]
    [string[]]$Args
)

$RootDir = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$HcDir = Join-Path $RootDir "nodes\nova\homelab-controller"

function Show-Help {
    @"
oc — Homelab Controller CLI (Windows)

Commands:
  slo                   Show current SLO status
  slo eval              Run SLO evaluation
  slo report            Generate SLO reports
  slo burn              Show burn rates
  slo budget            Show error budgets
  backup                Run Jasper backup
  help                  Show this help
"@
}

function Invoke-Slo {
    param([string]$SubCmd = "status")

    $ArtifactDir = Join-Path $HcDir "artifacts\slo"
    $CurrentJson = Join-Path $ArtifactDir "current.json"

    switch ($SubCmd) {
        "status" {
            if (Test-Path $CurrentJson) {
                $data = Get-Content $CurrentJson | ConvertFrom-Json
                $s = $data.summary
                Write-Host "=== SLO Status ==="
                Write-Host "Last evaluated: $($data.timestamp)"
                Write-Host "SLOs: $($s.total_slos) total"
                Write-Host "  ✅ $($s.slos_meeting_objective) meeting objective"
                Write-Host "  ⚠️  $($s.slos_at_risk) at risk"
                Write-Host "  🔴 $($s.slos_exhausted) budget exhausted"
            } else {
                Write-Host "No SLO data. Run evaluation on Nova first."
            }
        }
        "eval" {
            Write-Host "SLO evaluation runs on Nova (Linux). SSH in and run: oc slo eval"
        }
        default {
            Write-Host "Unknown slo subcommand: $SubCmd"
            Write-Host "Try: oc.ps1 slo [status|eval|report|burn|budget]"
        }
    }
}

switch ($Command) {
    "slo" {
        $sub = if ($Args.Count -gt 0) { $Args[0] } else { "status" }
        Invoke-Slo -SubCmd $sub
    }
    "backup" {
        & "$RootDir\tools\backup\windows\LabBackup.ps1"
    }
    "help" { Show-Help }
    default {
        Write-Host "Unknown command: $Command"
        Show-Help
    }
}
