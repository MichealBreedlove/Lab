# SetupScheduledTask.ps1 — Create a Windows Scheduled Task for daily Lab backup
# Run as Administrator

$TaskName = "LabBackup"
$ScriptPath = "$env:USERPROFILE\Lab\tools\backup\windows\LabBackup.ps1"

# Remove existing task if present
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

# Create trigger: daily at 2:30 AM
$Trigger = New-ScheduledTaskTrigger -Daily -At "2:30AM"

# Create action
$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`"" `
    -WorkingDirectory "$env:USERPROFILE\Lab"

# Settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

# Register
Register-ScheduledTask `
    -TaskName $TaskName `
    -Trigger $Trigger `
    -Action $Action `
    -Settings $Settings `
    -Description "Daily Lab GitHub backup for Jasper node" `
    -RunLevel Highest

Write-Host "=== Scheduled task '$TaskName' created ==="
Write-Host "Runs daily at 2:30 AM"
Write-Host "Script: $ScriptPath"
Write-Host ""
Write-Host "To test now: Start-ScheduledTask -TaskName $TaskName"
