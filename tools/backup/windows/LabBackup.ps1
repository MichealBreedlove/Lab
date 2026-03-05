# LabBackup.ps1 — Collect Jasper state, sanitize, commit, push
# Run as scheduled task or manually
$ErrorActionPreference = "Continue"

$RepoDir = "$env:USERPROFILE\Lab"
$NodeDir = "$RepoDir\nodes\jasper"
$Date = Get-Date -Format "yyyy-MM-dd"
$Time = Get-Date -Format "HH:mm"

Write-Host "=== Lab backup: jasper @ $Date $Time ==="

# Ensure repo is up to date
Set-Location $RepoDir
git pull --rebase --quiet 2>$null

# Create directories
@("openclaw\config", "openclaw\scripts", "windows\scheduled_tasks", "logs") | ForEach-Object {
    New-Item -ItemType Directory -Path "$NodeDir\$_" -Force | Out-Null
}

# --- Collect OpenClaw info ---
Write-Host "Collecting OpenClaw info..."
$ocVersion = try { openclaw --version 2>&1 } catch { "Not installed" }
$ocStatus = try { openclaw status 2>&1 } catch { "Status unavailable" }

@"
# OpenClaw State — Jasper
Generated: $Date $Time

## Version
$ocVersion

## Status
$ocStatus
"@ | Out-File -FilePath "$NodeDir\openclaw\status.md" -Encoding utf8

# --- Collect system info ---
Write-Host "Collecting system info..."
$sysInfo = @"
# System State — Jasper
Generated: $Date $Time

## OS
$(Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber | Format-List | Out-String)

## CPU
$(Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors | Format-List | Out-String)

## Memory
$(Get-CimInstance Win32_PhysicalMemory | Measure-Object Capacity -Sum | ForEach-Object { "$([math]::Round($_.Sum/1GB, 1)) GB total" })

## Disk
$(Get-PSDrive -PSProvider FileSystem | Select-Object Name, @{N='Used(GB)';E={[math]::Round($_.Used/1GB,1)}}, @{N='Free(GB)';E={[math]::Round($_.Free/1GB,1)}} | Format-Table | Out-String)

## GPU
$(Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion | Format-List | Out-String)
"@

$sysInfo | Out-File -FilePath "$NodeDir\windows\system_state.md" -Encoding utf8

# --- Sanitize ---
Write-Host "Sanitizing..."
& "$RepoDir\tools\backup\windows\Sanitize.ps1" -Path $NodeDir

# --- Commit & Push ---
Write-Host "Committing..."
Set-Location $RepoDir
git add "nodes/jasper/" 2>$null
git add -A 2>$null

$diff = git diff --cached --quiet 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "No changes to commit."
} else {
    git commit -m "node:jasper backup $Date $Time" --quiet
    Write-Host "Pushing..."
    git push --quiet 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Push failed (will retry next run)"
    }
}

Write-Host "=== Backup complete: jasper ==="
