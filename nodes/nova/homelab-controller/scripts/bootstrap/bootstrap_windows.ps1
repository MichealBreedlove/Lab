# P31 — Bootstrap Windows Helper (Gateway-Side)
# Configures OpenClaw gateway, Git, SSH, and scheduled tasks on Windows nodes
param(
    [string]$NodeName = "jasper",
    [string]$GatewayHost = "10.1.1.150",
    [int]$GatewayPort = 18789,
    [switch]$DryRun = $true,
    [switch]$Apply
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"

if ($Apply) { $DryRun = $false }

Write-Host "=== Bootstrap Windows: $NodeName ($timestamp) ==="
Write-Host "  Mode: $(if ($DryRun) { 'DRY-RUN' } else { 'APPLY' })"

$steps = @()

# Step 1: Check Git
$gitPath = Get-Command git -ErrorAction SilentlyContinue
$steps += @{
    name = "git_installed"
    pass = $null -ne $gitPath
    detail = if ($gitPath) { $gitPath.Source } else { "git not found in PATH" }
}

# Step 2: Check OpenSSH client
$sshPath = Get-Command ssh -ErrorAction SilentlyContinue
$steps += @{
    name = "ssh_client"
    pass = $null -ne $sshPath
    detail = if ($sshPath) { $sshPath.Source } else { "ssh not found" }
}

# Step 3: Check PowerShell version
$psVer = $PSVersionTable.PSVersion
$steps += @{
    name = "powershell_version"
    pass = $psVer.Major -ge 7
    detail = "PowerShell $($psVer.ToString())"
}

# Step 4: Check OpenClaw installed
$ocPath = Get-Command openclaw -ErrorAction SilentlyContinue
$steps += @{
    name = "openclaw_installed"
    pass = $null -ne $ocPath
    detail = if ($ocPath) { $ocPath.Source } else { "openclaw not found" }
}

# Step 5: Check OpenClaw gateway config
$ocConfig = Join-Path $env:USERPROFILE ".openclaw\openclaw.json"
$configExists = Test-Path $ocConfig
$steps += @{
    name = "openclaw_config"
    pass = $configExists
    detail = if ($configExists) { $ocConfig } else { "Config not found at $ocConfig" }
}

# Step 6: Check gateway port listening
$portCheck = $false
try {
    $tcp = New-Object System.Net.Sockets.TcpClient
    $tcp.Connect($GatewayHost, $GatewayPort)
    $portCheck = $true
    $tcp.Close()
} catch {}
$steps += @{
    name = "gateway_port"
    pass = $portCheck
    detail = "${GatewayHost}:${GatewayPort}"
}

# Step 7: Check Lab repo clone
$labPath = Join-Path $env:TEMP "Lab-audit"
$labExists = Test-Path (Join-Path $labPath ".git")
$steps += @{
    name = "lab_repo"
    pass = $labExists
    detail = if ($labExists) { $labPath } else { "Not found at $labPath" }
}

# Step 8: Check SSH key
$sshKey = Join-Path $env:USERPROFILE ".ssh\id_ed25519"
$keyExists = Test-Path $sshKey
$steps += @{
    name = "ssh_key"
    pass = $keyExists
    detail = if ($keyExists) { $sshKey } else { "No key at $sshKey" }
}

# Print results
$passing = ($steps | Where-Object { $_.pass }).Count
$total = $steps.Count
$icon = if ($passing -eq $total) { "✅" } else { "❌" }

Write-Host ""
Write-Host "$icon Windows Bootstrap: $passing/$total checks passing"
foreach ($s in $steps) {
    $si = if ($s.pass) { "✅" } else { "❌" }
    Write-Host "  $si $($s.name): $($s.detail)"
}

# Write artifact
$artifactsDir = Join-Path (Split-Path $PSScriptRoot) "..\artifacts\bootstrap"
if (-not (Test-Path $artifactsDir)) { New-Item -ItemType Directory -Path $artifactsDir -Force | Out-Null }

$result = @{
    timestamp = $timestamp
    node = $NodeName
    platform = "windows"
    dry_run = $DryRun
    checks = $steps
    summary = @{ total = $total; passing = $passing; failing = $total - $passing }
    pass = ($passing -eq $total)
} | ConvertTo-Json -Depth 4

$result | Out-File (Join-Path $artifactsDir "bootstrap_${NodeName}.json") -Encoding UTF8

Write-Host ""
Write-Host "Artifact written: artifacts/bootstrap/bootstrap_${NodeName}.json"

if ($passing -eq $total) { exit 0 } else { exit 1 }
