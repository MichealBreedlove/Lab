# Morning Brief -- sends daily system + personal summary to Telegram
# Runs via scheduled task at 8:00 AM daily
$ErrorActionPreference = "SilentlyContinue"

# ── Cluster Health
$targets = (Invoke-RestMethod "http://10.1.1.25:9090/api/v1/targets").data.activeTargets
$up   = ($targets | Where-Object health -eq "up").Count
$total = $targets.Count
$down = $targets | Where-Object health -ne "up"
if ($down) {
    $downNames = ($down | ForEach-Object { $_.labels.instance }) -join ", "
    $healthLine = "[!!] $up/$total targets UP -- DOWN: $downNames"
} else {
    $healthLine = "[OK] $up/$total targets UP"
}

# ── Active Alerts
$alerts = (Invoke-RestMethod "http://10.1.1.25:9090/api/v1/alerts").data.alerts |
    Where-Object { $_.state -eq "firing" }
if ($alerts) {
    $alertNames = ($alerts | ForEach-Object { $_.labels.alertname }) -join ", "
    $alertLine = "[ALERT] $($alerts.Count) firing: $alertNames"
} else {
    $alertLine = "[OK] No active alerts"
}

# ── Cluster Tasks
$TOKEN = "hlab_94265cc3491a9340853793f8d8e3a0611f76946f0756d350"
$tasks = (Invoke-RestMethod "http://10.1.1.21:8081/cluster/tasks" -Headers @{Authorization="Bearer $TOKEN"}).summary
$taskLine = "Tasks -- completed: $($tasks.completed)  queued: $($tasks.queued)  failed: $($tasks.failed)"

# ── Jasper GPU
$gpuRaw = & "C:\Windows\System32\nvidia-smi.exe" --query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total --format=csv,noheader,nounits 2>$null
if ($gpuRaw) {
    $g = ($gpuRaw -split ",") | ForEach-Object { $_.Trim() }
    $gpuLine = "GPU: $($g[0]) | Temp: $($g[1])C | Util: $($g[2])% | VRAM: $($g[3])/$($g[4]) MiB"
} else {
    $gpuLine = "GPU: unavailable"
}

# ── Jasper Disk
$disk = Get-PSDrive C | Select-Object Used, Free
$usedGB  = [math]::Round($disk.Used  / 1GB, 1)
$totalGB = [math]::Round(($disk.Used + $disk.Free) / 1GB, 1)
$pct     = [math]::Round(($disk.Used / ($disk.Used + $disk.Free)) * 100)
$diskLine = "Disk C: $usedGB/$totalGB GB ($pct% used)"

# ── Weather
$weather = (Invoke-WebRequest "https://wttr.in/Fairfield,CA?format=%C+%t+%h&m" -UseBasicParsing).Content.Trim()
$weatherLine = "Weather (Fairfield): $weather"

# ── Date + compose
$date = Get-Date -Format "dddd, MMMM d, yyyy"
$time = Get-Date -Format "HH:mm"

$msg = "Morning Brief -- $date $time PDT

CLUSTER
$healthLine
$alertLine
$taskLine

JASPER
$gpuLine
$diskLine

LOCAL
$weatherLine

CERT PATH: A+ > Network+ > Security+ > Linux+ > CySA+"

# ── Log to file (OpenClaw heartbeat picks this up)
$logPath = "C:\Users\mikej\.openclaw\workspace\memory\morning-briefs.log"
"[$((Get-Date).ToString('yyyy-MM-dd HH:mm'))]" | Add-Content $logPath -Encoding UTF8
$msg | Add-Content $logPath -Encoding UTF8
"---" | Add-Content $logPath -Encoding UTF8

Write-Host $msg
